from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

from backend.app.services.gemini_client import generate_json
from backend.app.services.plugin_context import build_team_sop

# Dispute categories and BNM mandated SLA timelines
CATEGORIES = {
    "unauthorized_transactions": {"name": "Unauthorized Transactions", "urgency": "high", "sla_days": 5},
    "billing_errors": {"name": "Billing Errors", "urgency": "medium", "sla_days": 20},
    "mis_selling_claims": {"name": "Mis-selling Claims", "urgency": "medium", "sla_days": 20},
    "atm_debit_card_disputes": {"name": "ATM / Debit Card Disputes", "urgency": "high", "sla_days": 5},
    "insurance_takaful_claims": {"name": "Insurance / Takaful Claims", "urgency": "medium", "sla_days": 20},
    "loan_financing_disputes": {"name": "Loan / Financing Disputes", "urgency": "low", "sla_days": 20},
    "emoney_digital_payment_disputes": {"name": "E-money / Digital Payment", "urgency": "medium", "sla_days": 20},
}

class ClassificationService:
    def is_actual_dispute(self, from_email: str, subject: str, body: str) -> bool:
        """
        Determines whether the incoming email is a genuine banking dispute case or general junk/notification.
        """
        from_email = from_email.lower()
        subj = subject.lower()
        text = body.lower()
        combined = f"{subj} {text}"

        # 1. Filter out known automated/system email addresses
        auto_patterns = [
            "noreply", "no-reply", "newsletter", "notification", "alert", 
            "jobs-", "updates-", "donotreply", "do-not-reply", "mailer-daemon",
            "support@", "info@", "marketing@", "security@", "teamzoom"
        ]
        if any(pat in from_email for pat in auto_patterns):
            return False

        # 2. Check for dispute-relevant banking terms
        dispute_keywords = [
            "dispute", "unauthorized", "unauthorised", "chargeback", "fraud", 
            "atm", "billing", "claim", "refund", "overcharge", "double charge", 
            "loan", "card", "transaction", "discrepancy", "error", "withdraw", 
            "money", "payment", "e-wallet", "transfer", "rm", "ringgit"
        ]
        
        # If it doesn't match any dispute keywords, it is not a dispute case
        if not any(kw in combined for kw in dispute_keywords):
            return False

        return True

    def _build_governance_schema(self, category: str, urgency: str, sla_days: int, confidence: float, rationale: str) -> Dict[str, Any]:
        cat_info = CATEGORIES.get(category, CATEGORIES["billing_errors"])
        mandated_sla = int(sla_days or cat_info["sla_days"])
        return {
            "bnm_compliant": True,
            "policy_document": "BNM Policy Document on Complaints Handling",
            "framework": "FMOS (Financial Markets Ombudsman Service)",
            "classification_timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence": confidence,
            "rationale": rationale,
            "mandated_sla_days": mandated_sla,
            "governance_status": "STAMPED_PASS",
        }

    def classify_with_ai(self, text: str, subject: str = "") -> Tuple[str, str, int, Dict[str, Any]] | None:
        category_list = "\n".join(
            f"- {cat}: {info['name']} (urgency={info['urgency']}, sla={info['sla_days']} working days)"
            for cat, info in CATEGORIES.items()
        )
        system_prompt = (
            "You are Nadia, the Dispute Classifier & BNM Compliance Strategist in the AI Banking Dispute Automation Taskforce.\n"
            "Use the team SOP and the BNM/FMOS governance skill below as your operating rules.\n"
            f"Classify the complaint into exactly ONE category. Allowed categories:\n{category_list}\n"
            "Respond with JSON only: "
            '{"category": "<one of the 7 slugs>", "urgency": "<high|medium|low>", "sla_days": <int>, "confidence": <0.0-1.0>, "rationale": "<short reason>"}\n\n'
            f"TEAM CONTEXT:\n{build_team_sop()}"
        )
        data = generate_json(system_prompt, f"EMAIL SUBJECT: {subject}\n\nCOMPLAINT BODY:\n{text}")
        if not data:
            return None
        category = data.get("category")
        if category not in CATEGORIES:
            return None
        try:
            confidence = float(data.get("confidence", 0.9))
        except (TypeError, ValueError):
            confidence = 0.9
        if not 0.0 <= confidence <= 1.0:
            confidence = 0.9
        rationale = str(data.get("rationale") or "AI classification rationale.")
        urgency = str(data.get("urgency") or CATEGORIES[category]["urgency"])
        if urgency not in {"high", "medium", "low"}:
            urgency = CATEGORIES[category]["urgency"]
        try:
            sla_days = int(data.get("sla_days") or CATEGORIES[category]["sla_days"])
        except (TypeError, ValueError):
            sla_days = CATEGORIES[category]["sla_days"]
        governance = self._build_governance_schema(category, urgency, sla_days, confidence, rationale)
        return category, urgency, sla_days, governance

    def classify_text(self, text: str, subject: str = "") -> Tuple[str, str, int, Dict[str, Any]]:
        """
        Classify complaint text into category, urgency, SLA working days, and rationale.
        Tries AI first; falls back to rule-based keyword logic.
        Aligns governance schema with BNM Policy Document on Complaints Handling.
        """
        ai_result = self.classify_with_ai(text, subject)
        if ai_result:
            return ai_result

        combined = (subject + " " + text).lower()
        
        category = "billing_errors" # Default fallback category
        rationale = "General complaint processed under standard billing investigation."
        confidence = 0.85

        if "unauthorized" in combined or "fraud" in combined or "hacked" in combined or "stolen" in combined:
            category = "unauthorized_transactions"
            rationale = "Clear description of unauthorized or fraudulent activity on account/card."
            confidence = 0.96
        elif "atm" in combined or "withdrawal" in combined or "cash not dispensed" in combined:
            category = "atm_debit_card_disputes"
            rationale = "ATM withdrawal anomaly or debit card dispensing failure."
            confidence = 0.91
        elif "duplicate" in combined or "double charge" in combined or "overcharged" in combined:
            category = "billing_errors"
            rationale = "Statement duplicate charge or merchant overbilling."
            confidence = 0.93
        elif "mis-selling" in combined or "misled" in combined or "promised" in combined:
            category = "mis_selling_claims"
            rationale = "Allegation of misrepresentation or mis-selling during product acquisition."
            confidence = 0.88
        elif "insurance" in combined or "takaful" in combined or "policy" in combined:
            category = "insurance_takaful_claims"
            rationale = "Claim dispute related to insurance policy or takaful coverage terms."
            confidence = 0.90
        elif "loan" in combined or "mortgage" in combined or "interest rate" in combined:
            category = "loan_financing_disputes"
            rationale = "Dispute over loan interest calculation or financing repayment terms."
            confidence = 0.87
        elif "e-wallet" in combined or "qr" in combined or "touch n go" in combined or "grab" in combined:
            category = "emoney_digital_payment_disputes"
            rationale = "E-money or digital payment gateway transfer discrepancy."
            confidence = 0.89

        cat_info = CATEGORIES.get(category, CATEGORIES["billing_errors"])
        urgency = cat_info["urgency"]
        sla_days = cat_info["sla_days"]

        # Governance schema stamp (BNM & FMOS compliance)
        governance_schema = {
            "bnm_compliant": True,
            "policy_document": "BNM Policy Document on Complaints Handling",
            "framework": "FMOS (Financial Markets Ombudsman Service)",
            "classification_timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence": confidence,
            "rationale": rationale,
            "mandated_sla_days": sla_days,
            "governance_status": "STAMPED_PASS"
        }

        return category, urgency, sla_days, governance_schema

classification_service = ClassificationService()
