import logging
from typing import Optional
from backend.app.services.gemini_client import generate_json

logger = logging.getLogger("aduanflow")

# Keys + patterns the AI will be asked to extract from the email body
FIELDS = {
    "customer_name": "Full name of the complainant (from body signature if present, else sender name)",
    "account_number": "Account number or card number. Common formats: full 10-12 digit number, or 'ending XXXX' / 'ending in XXXX' / 'card ending XXXX'. Output only the digits if a partial is given (e.g. 8842), else null.",
    "nric": "Malaysian NRIC in format dddddd-dd-dddd, if present, else null",
    "amount": "Dispute amount in MYR as a number (no currency symbol). e.g. 620.00, else null",
    "incident_date": "Date of the disputed transaction as YYYY-MM-DD, if present, else null",
}


class EntityExtractionService:
    def extract(self, email_body: str, sender_name: str = "Customer", fallback_amount: float = 1500.0) -> dict:
        """
        Use Gemini to extract structured banking-dispute entities from an email body.
        Falls back to regex when the AI is unavailable, and to defaults when nothing is found.
        """
        if not email_body or not email_body.strip():
            return self._defaults(sender_name, fallback_amount)

        system_prompt = (
            "You are an OCR/document-parsing agent for a banking dispute automation system.\n"
            "Extract the following fields from the customer complaint email. Return ONLY JSON.\n\n"
            + "\n".join(f"- {key}: {desc}" for key, desc in FIELDS.items())
            + "\n\n"
            "Rules:\n"
            "- amount: numeric only, no currency symbol, no commas (e.g. 620.00).\n"
            "- account_number: if the text says 'ending'/'card ending'/'a/c', return the 4 digits only.\n"
            "- If a field is not present in the email, set it to null.\n"
            'Response format: {"customer_name": ..., "account_number": ..., "nric": ..., "amount": ..., "incident_date": ...}'
        )
        user_prompt = f"Sender name from email header: {sender_name}\n\nEmail body:\n{email_body}"

        try:
            data = generate_json(system_prompt, user_prompt)
            if data and isinstance(data, dict):
                return self._normalize(data, sender_name, fallback_amount)
        except Exception as exc:
            logger.warning(f"[EntityExtraction] AI extraction failed, falling back to regex: {exc}")

        return self._regex_fallback(email_body, sender_name, fallback_amount)

    def _normalize(self, data: dict, sender_name: str, fallback_amount: float) -> dict:
        import re
        amount = data.get("amount")
        if isinstance(amount, str):
            amount = re.sub(r"[^\d.]", "", amount)
        try:
            amount = float(amount) if amount else None
        except (ValueError, TypeError):
            amount = None

        account = data.get("account_number")
        if account is not None and str(account).strip().lower() in ("null", "none", "n/a", ""):
            account = None

        nric = data.get("nric")
        if nric is not None and str(nric).strip().lower() in ("null", "none", "n/a", ""):
            nric = None

        name = data.get("customer_name")
        if not name or str(name).strip().lower() in ("null", "none", "unknown", ""):
            name = sender_name

        return {
            "customer_name": str(name).strip() or sender_name,
            "account_number": str(account).strip() if account else None,
            "nric": str(nric).strip() if nric else None,
            "amount": amount if amount is not None and amount > 0 else fallback_amount,
            "incident_date": (str(data.get("incident_date") or "").strip() or None),
        }

    def _regex_fallback(self, email_body: str, sender_name: str, fallback_amount: float) -> dict:
        import re
        # Try full account number first (10-12 contiguous digits)
        full_acc_match = re.search(r'\b(\d{10,12})\b', email_body)
        # Try "ending XXXX" / "card ending XXXX" pattern for partial accounts
        partial_acc_match = re.search(
            r'(?:ending|card ending|a/c ending)\s+(?:in\s+)?(?::)?\s*(\d{4})', email_body, re.IGNORECASE
        )
        if full_acc_match:
            account_number = full_acc_match.group(1)
        elif partial_acc_match:
            # Store as "****XXXX" so masking produces the correct format
            account_number = partial_acc_match.group(1)
        else:
            account_number = None

        nric_match = re.search(r'\b\d{6}-\d{2}-\d{4}\b', email_body)
        amt_match = re.search(r'(?:RM|\$)\s*([\d,]+(?:\.\d{2})?)', email_body, re.IGNORECASE)
        amount = fallback_amount
        if amt_match:
            try:
                amount = float(amt_match.group(1).replace(",", ""))
            except Exception:
                amount = fallback_amount
        date_match = re.search(r'\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b', email_body)
        return {
            "customer_name": sender_name,
            "account_number": account_number,
            "nric": nric_match.group(0) if nric_match else None,
            "amount": amount,
            "incident_date": date_match.group(1) if date_match else None,
        }


    def _defaults(self, sender_name: str, fallback_amount: float) -> dict:
        return {
            "customer_name": sender_name,
            "account_number": None,
            "nric": None,
            "amount": fallback_amount,
            "incident_date": None,
        }


entity_extraction_service = EntityExtractionService()
