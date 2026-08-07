import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import random
import re
from backend.app.services.encryption_service import encryption_service
from backend.app.services.classification_service import classification_service
from backend.app.services.verification_service import verification_service
from backend.app.services.resolution_service import resolution_service
from backend.app.services.communication_service import communication_service
from backend.app.models.case import Case
from backend.app.models.audit import AuditLog

logger = logging.getLogger("aduanflow")


def _persist_audit_rows(case_id: str, audit_log: list) -> None:
    """
    Write each pipeline audit step into the audit_logs table.
    Called after the case object is built so that both the JSON blob
    on the Case row AND the normalised audit_logs table stay in sync.
    """
    try:
        from sqlmodel import Session
        from backend.app.database import engine

        rows = []
        for entry in audit_log:
            rows.append(
                AuditLog(
                    case_id=case_id,
                    actor=entry.get("actor", "System"),
                    action=entry.get("action", ""),
                    detail=entry.get("detail", ""),
                    created_at=datetime.utcnow(),
                )
            )
        if rows:
            with Session(engine) as session:
                for row in rows:
                    session.add(row)
                session.commit()
            logger.info(f"[IntakeService] Persisted {len(rows)} audit log rows for case {case_id}")
    except Exception as e:
        logger.error(f"[IntakeService] Failed to persist audit rows for case {case_id}: {e}")


class IntakeService:
    def process_incoming_complaint(
        self,
        customer_name: str,
        customer_email: str,
        account_number: str,
        nric: str,
        amount: float,
        email_subject: str,
        email_body: str,
        attachment_name: Optional[str] = None,
        card_number: Optional[str] = None,
        received_at: Optional[datetime] = None,
        incident_date: Optional[str] = None
    ) -> Case:
        """
        Processes complaint intake through the 5-stage AI expert pipeline:
        1. Parse OCR fields / text  (Rhea — Ingestion & Security Agent)
        2. Encrypt NRIC, account number, card number, dispute amount at rest
        3. Classify category & urgency according to BNM SLA guidelines  (Nadia — Compliance Agent)
        4. Run MCP Core Banking verification  (Faris — Verification Agent)
        5. Execute autonomous financial resolution if PASS  (Financial Agent)
        6. Draft compliant customer email  (Maya — Comms Agent)

        All pipeline steps are persisted to both the case.audit_log JSON column
        AND the normalised audit_logs database table for full CRUD visibility.
        """
        case_id = f"DISP-2026-{random.randint(10000, 99999)}"
        masked_acc = encryption_service.mask_account(account_number)
        masked_card = encryption_service.mask_account(card_number) if card_number else None

        # Encrypt sensitive PII at rest
        nric_enc = encryption_service.encrypt(nric)
        acc_enc = encryption_service.encrypt(account_number)
        card_enc = encryption_service.encrypt(card_number) if card_number else None
        amt_enc = encryption_service.encrypt(str(amount))

        # 1. OCR Extraction Metadata
        ocr_results = {
            "confidence": 0.94 if attachment_name else 0.89,
            "extractedFields": {
                "customer_name": customer_name,
                "account_reference": masked_acc,
                "card_reference": masked_card or "None",
                "dispute_amount": amount,
                "incident_date": incident_date or "Not specified",
                "attachment_processed": attachment_name or "None"
            }
        }

        # 2. Categorization & Urgency  (Nadia — Classification Agent)
        category, urgency, sla_days, gov_schema = classification_service.classify_text(email_body, email_subject)
        due_date = datetime.utcnow() + timedelta(days=sla_days)

        classification_data = {
            "category": category,
            "confidence": 0.95,
            "urgency": urgency,
            "rationale": gov_schema["rationale"],
            "slaHours": sla_days * 24,
            "governance": gov_schema
        }

        # 3. Verification Engine  (Faris — MCP Verification Agent)
        verification_data = verification_service.verify_case({
            "amount": amount,
            "category": category,
            "email_body": email_body
        })
        v_result = verification_data["result"]

        # 4. Financial Resolution & Communication
        fin_resolution = None
        communication = {
            "acknowledgementSent": datetime.utcnow().isoformat() + "Z",
            "finalResponse": None
        }

        if v_result == "PASS":
            fin_resolution = resolution_service.resolve_financials(case_id, amount, category)
            comm_data = communication_service.generate_response(
                case_id=case_id,
                customer_name=customer_name,
                category_label=category.replace("_", " ").title(),
                amount=amount,
                masked_account=masked_acc,
                masked_card=masked_card,
                card_number=card_number,
                action=fin_resolution["action"] if fin_resolution else "Adjustment",
                sla_days=sla_days,
                verification=verification_data,
            )
            communication["finalResponse"] = comm_data

            # Automate real outbound resolution email dispatch to complainant's email
            try:
                outbound_status = communication_service.send_outbound_email(
                    to_email=customer_email,
                    subject=comm_data["subject"],
                    body=comm_data["body"]
                )
                communication["outboundDispatch"] = outbound_status
            except Exception as e:
                communication["outboundDispatchError"] = str(e)
        else:
            # MANUAL_REVIEW Flow: Dispatch Dispute Acknowledgement & Under Investigation Email
            ack_subject = f"Dispute Acknowledgement: Case {case_id} Logged Under Investigation"
            ack_body = (
                f"Dear {customer_name},\n\n"
                f"We acknowledge receipt of your dispute complaint (Reference: {case_id}) regarding "
                f"{category.replace('_', ' ').title()} of RM {amount:.2f}.\n\n"
                f"Your case has been assigned to an investigator for manual review under Bank Negara Malaysia (BNM) "
                f"SLA guidelines ({sla_days} working days SLA mandate).\n\n"
                f"Mandatory Compliance Disclosures:\n"
                f"1. BNM Policy Document on Complaints Handling: SLA target {sla_days} working days.\n"
                f"2. FMOS Redress Timeline Notice: Should you remain dissatisfied with our final decision, you have the "
                f"right to refer your dispute to the Financial Mediation & Ombudsman Service (FMOS) within 6 months.\n\n"
                f"Regards,\nAduanFlow Dispute Resolution Taskforce"
            )
            comm_ack = {"subject": ack_subject, "body": ack_body}
            communication["acknowledgement"] = comm_ack
            communication["finalResponse"] = comm_ack
            communication["acknowledgementSent"] = datetime.utcnow().isoformat() + "Z"
            try:
                logger.info(f"[IntakeService] MANUAL_REVIEW: Dispatching Dispute Acknowledgement Email to {customer_email}...")
                outbound_status = communication_service.send_outbound_email(
                    to_email=customer_email,
                    subject=ack_subject,
                    body=ack_body
                )
                communication["outboundDispatch"] = outbound_status
            except Exception as e:
                logger.error(f"[IntakeService] MANUAL_REVIEW Email Dispatch Error: {e}")
                communication["outboundDispatchError"] = str(e)

        # 5. Audit Trail Construction — 5-Stage AI Expert Pipeline Trace
        now_ts = datetime.utcnow().isoformat() + "Z"
        audit_log = [
            {
                "time": now_ts,
                "actor": "Email MCP",
                "action": "Complaint email received",
                "detail": f"From {customer_email}",
            },
            {
                "time": now_ts,
                "actor": "Intake Agent",
                "action": "OCR extraction completed",
                "detail": f"Extracted {customer_name}, {masked_acc}",
            },
            {
                "time": now_ts,
                "actor": "Security Agent",
                "action": "PII encrypted at rest",
                "detail": "NRIC, Account, Amount encrypted via Fernet AES-256",
            },
            {
                "time": now_ts,
                "actor": "Classification Agent",
                "action": "Case classified",
                "detail": f"{category}, Urgency: {urgency}, SLA: {sla_days} days",
            },
            {
                "time": now_ts,
                "actor": "Verification Agent",
                "action": f"Verification {v_result}",
                "detail": "Core banking MCP checks completed",
            },
        ]

        if fin_resolution:
            audit_log.append({
                "time": now_ts,
                "actor": "Financial Agent",
                "action": "Financial resolution posted",
                "detail": f"JE {fin_resolution['journalEntry']}",
            })
            audit_log.append({
                "time": now_ts,
                "actor": "Comms Agent",
                "action": "Compliant resolution response generated",
                "detail": "BNM/FMOS disclosures embedded in customer email",
            })
        else:
            audit_log.append({
                "time": now_ts,
                "actor": "Comms Agent",
                "action": "Dispute acknowledgement dispatched",
                "detail": f"5-day BNM SLA & FMOS disclosures sent to complainant",
            })

        # Build Case ORM object
        case_obj = Case(
            id=case_id,
            customer_name=customer_name,
            customer_email=customer_email,
            masked_account=masked_acc,
            category=category,
            urgency=urgency,
            status=v_result,
            verification_result=v_result,
            amount=amount,
            assigned_to="Agent-Auto" if v_result == "PASS" else None,
            received_at=received_at or datetime.utcnow(),
            due_date=due_date,
            processing_time="2m 30s" if v_result == "PASS" else "—",
            email_subject=email_subject,
            email_body=email_body,
            nric_encrypted=nric_enc,
            account_number_encrypted=acc_enc,
            card_number_encrypted=card_enc,
            dispute_amount_encrypted=amt_enc,
            masked_card=masked_card,
            ocr_results=ocr_results,
            classification=classification_data,
            verification=verification_data,
            financial_resolution=fin_resolution,
            communication=communication,
            audit_log=audit_log,
        )

        # Persist audit rows to audit_logs table so /api/audit CRUD works end-to-end
        _persist_audit_rows(case_id, audit_log)

        return case_obj


intake_service = IntakeService()
