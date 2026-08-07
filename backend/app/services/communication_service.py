from dotenv import load_dotenv
import os
load_dotenv()

from jinja2 import Template
from typing import Dict, Any

from backend.app.services.gemini_client import generate_json
from backend.app.services.plugin_context import build_team_sop

EMAIL_TEMPLATE = """Dear {{ customer_name }},

Thank you for bringing this matter to our attention. We have completed our investigation into your dispute (Reference: {{ case_id }}).

Investigation Summary: {{ investigation_summary }}

Resolution: A {{ action }} of RM {{ amount }} has been applied to your {{ account_ref }}.

Mandatory Compliance Disclosures:
1. BNM Policy Document on Complaints Handling Mandate: Resolution processed within {{ sla_days }} working days.
2. FMOS Redress Timeline Notice: Should you remain dissatisfied with this resolution, you have the right to refer your complaint to the Financial Mediation & Ombudsman Service (FMOS) within 6 months from the date of this final decision notice (for claims up to RM 250,000).

If you have further questions, please contact our Customer Service at 1-300-88-XXXX.

Regards,
Complaints Resolution Team
AduanFlow AI — Automated Banking Dispute Processing System"""

class CommunicationService:
    def _ai_investigation_summary(self, case_id: str, category_label: str, amount: float, verification: Dict[str, Any] | None) -> str | None:
        if not verification:
            return None
        result = verification.get("result") or "PASS"
        system_prompt = (
            "You are Maya, the Customer Communications & Dashboard Specialist in the AI Banking Dispute Automation Taskforce.\n"
            "Write ONE concise, professional, 1-2 sentence investigation summary for a banking dispute resolution letter.\n"
            "Do NOT invent regulatory requirements or legal disclaimers.\n"
            "Respond with JSON only: {\"summary\": \"<text>\"}"
        )
        data = generate_json(
            system_prompt,
            f"Case {case_id}: {category_label} of RM {amount:,.2f}, verification outcome {result}.",
        )
        if not data or not isinstance(data.get("summary"), str):
            return None
        return data["summary"].strip()

    def generate_response(
        self,
        case_id: str,
        customer_name: str,
        category_label: str,
        amount: float,
        masked_account: str,
        action: str,
        sla_days: int,
        verification: Dict[str, Any] | None = None,
        masked_card: str | None = None,
        card_number: str | None = None,
    ) -> Dict[str, Any]:
        """Auto-populate email templates with BNM compliance disclosures and FMOS redress timelines."""
        default_summary = (
            f"We verified your claim regarding the {category_label} of RM {amount}. "
            "Our core banking records and logs confirm the details provided in your complaint."
        )
        investigation_summary = self._ai_investigation_summary(case_id, category_label, amount, verification) or default_summary

        # Build account/card reference line; include both when card is known.
        account_ref = f"account ending {masked_account}" if masked_account else "account"
        if masked_card:
            account_ref = f"{account_ref} (card ending {masked_card})"

        template = Template(EMAIL_TEMPLATE)
        body = template.render(
            case_id=case_id,
            customer_name=customer_name,
            category_label=category_label,
            amount=f"{amount:,.2f}",
            account_ref=account_ref,
            action=action,
            sla_days=sla_days,
            investigation_summary=investigation_summary,
        )
        from_email = "complaints.resolution@bank.com.my"
        try:
            from sqlmodel import Session
            from backend.app.database import engine
            from backend.app.models.settings import SystemSettings
            with Session(engine) as session:
                settings_obj = session.get(SystemSettings, "global_settings")
                if settings_obj and settings_obj.gmail_email:
                    from_email = settings_obj.gmail_email
        except Exception:
            pass

        return {
            "from": from_email,
            "subject": f"Resolution Notice: Dispute {case_id} — {category_label}",
            "body": body
        }

    def send_outbound_email(self, to_email: str, subject: str, body: str, sender_email: str = None, app_password: str = None) -> Dict[str, Any]:
        """
        Dispatches outbound resolution notice to target customer email.
        Attempts real Google SMTP transmission if credentials are provided or present in environment.
        """
        import os
        import re
        import smtplib
        import logging
        from datetime import datetime
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.header import Header

        logger = logging.getLogger("aduanflow")

        if to_email:
            to_email = re.sub(r'[<>\s"]', '', to_email)

        smtp_user = sender_email or os.getenv("SMTP_USER") or os.getenv("GMAIL_EMAIL")
        smtp_pass = app_password or os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD")

        # Fallback to Database SystemSettings if not in env
        real_app_password = None
        try:
            from sqlmodel import Session
            from backend.app.database import engine
            from backend.app.models.settings import SystemSettings
            from backend.app.services.encryption_service import encryption_service

            with Session(engine) as session:
                settings_obj = session.get(SystemSettings, "global_settings")
                if settings_obj:
                    if not smtp_user and settings_obj.gmail_email:
                        smtp_user = settings_obj.gmail_email
                    if settings_obj.gmail_app_password_encrypted:
                        real_app_password = encryption_service.decrypt(settings_obj.gmail_app_password_encrypted)
        except Exception as db_err:
            logger.debug(f"[CommunicationService] Could not load DB credentials: {db_err}")

        # Dynamic Self-Recipient Protection: Prevent sending outbound emails to whichever mailbox is active
        if smtp_user and to_email.lower() == smtp_user.lower():
            logger.info(f"[CommunicationService] Skipping physical dispatch to active bank mailbox {to_email}")
            return {"status": "skipped", "smtp_delivered": False, "reason": "Bank mailbox self-recipient protection"}

        smtp_sent = False
        smtp_error = None

        # 1. Attempt Real SMTP Transmission ONLY if App Password available
        if smtp_user and (smtp_pass or real_app_password):
            active_password = smtp_pass or real_app_password
            try:
                logger.info(f"[CommunicationService] Connecting to smtp.gmail.com:587 for real delivery to {to_email}...")
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = to_email
                msg['Subject'] = Header(subject, 'utf-8')
                msg.attach(MIMEText(body, 'plain', 'utf-8'))

                server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                server.starttls()
                server.login(smtp_user, active_password)
                server.send_message(msg)
                server.quit()

                smtp_sent = True
                logger.info(f"[CommunicationService] SUCCESS: Real physical email delivered to {to_email} via SMTP!")
            except Exception as e:
                smtp_error = str(e)
                logger.error(f"[CommunicationService] SMTP delivery attempt failed: {e}")

        # 2. Attempt Google OAuth 2.0 API Transmission (messages.send using DB Token or Env)
        if not smtp_sent:
            try:
                from sqlmodel import Session
                from backend.app.database import engine
                from backend.app.models.settings import SystemSettings
                from backend.app.services.encryption_service import encryption_service
                import requests
                import base64

                raw_refresh = os.getenv("GMAIL_REFRESH_TOKEN")
                raw_sender = os.getenv("GMAIL_EMAIL")

                with Session(engine) as session:
                    settings_obj = session.get(SystemSettings, "global_settings")
                    if settings_obj:
                        if not raw_refresh and settings_obj.gmail_refresh_token_encrypted:
                            try:
                                raw_refresh = encryption_service.decrypt(settings_obj.gmail_refresh_token_encrypted)
                            except Exception:
                                pass
                        if settings_obj.gmail_email:
                            raw_sender = settings_obj.gmail_email

                if raw_refresh:
                    raw_client_id = os.getenv("GOOGLE_CLIENT_ID") or "1041907708486-uvplue4dp8pl64bre8a36u0qs5vc8lsn.apps.googleusercontent.com"
                    raw_client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or "GOCSPX-AduanFlowAutoSecretKey2026"


                    access_token = None
                    token_res = requests.post("https://oauth2.googleapis.com/token", data={
                        "client_id": raw_client_id,
                        "client_secret": raw_client_secret,
                        "refresh_token": raw_refresh,
                        "grant_type": "refresh_token"
                    }, timeout=5)

                    if token_res.status_code == 200:
                        access_token = token_res.json().get("access_token")
                    elif raw_refresh.startswith("ya29."):
                        access_token = raw_refresh

                    if access_token:
                        msg = MIMEMultipart()
                        if raw_sender:
                            msg['From'] = raw_sender
                        msg['To'] = to_email
                        msg['Subject'] = Header(subject, 'utf-8')
                        msg.attach(MIMEText(body, 'plain', 'utf-8'))

                        raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()

                        api_res = requests.post(
                            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                            json={"raw": raw_msg},
                            timeout=10
                        )
                        if api_res.status_code == 200:
                            smtp_sent = True
                            logger.info(f"[CommunicationService] SUCCESS: Real physical email delivered to {to_email} via Google OAuth 2.0 Gmail API!")
                        else:
                            logger.error(f"[CommunicationService] Gmail REST API returned status {api_res.status_code}: {api_res.text}")
            except Exception as oauth_err:
                logger.error(f"[CommunicationService] OAuth Gmail API dispatch error: {oauth_err}")

        effective_sender = smtp_user or "complaints@aduanflow.bank"
        logger.info(f"[CommunicationService] Outbound notice recorded for {to_email} via {effective_sender}")

        return {
            "status": "sent" if smtp_sent else "recorded",
            "smtp_delivered": smtp_sent,
            "smtp_error": smtp_error,
            "sender": effective_sender,
            "recipient": to_email,
            "subject": subject,
            "body_snippet": body[:120] + "...",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

communication_service = CommunicationService()
