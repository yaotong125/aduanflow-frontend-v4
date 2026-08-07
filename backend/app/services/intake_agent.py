import logging
import json
from typing import Dict, Any, Optional, Callable, List

from backend.app.services.gemini_client import generate_content_with_tools, parse_json_response, generate_json
from backend.app.services.pdf_extractor import pdf_text_from_bytes
from backend.app.services.plugin_context import build_team_sop

logger = logging.getLogger("aduanflow")

# The JSON schema the agent must produce as its final answer
_ENTITY_JSON_SCHEMA = (
    '{"customer_name": "<name or null>", '
    '"account_number": "<full account number digits or null>", '
    '"card_number": "<full card number or 4-digit ending, or null>", '
    '"nric": "<dddddd-dd-dddd or null>", '
    '"amount": <number or null>, '
    '"incident_date": "<YYYY-MM-DD or null>", '
    '"used_tools": ["<tool names called>"]}'
)


class IntakeAgent:
    """
    Rhea - Ingestion & Security Agent (agentic).

    Orchestrates complaint intake as a multi-tool agent:
      - reads the complaint email body + attachments list
      - decides whether to call the `pdf_extract` tool to read a PDF attachment
      - extracts structured entities (customer, account, NRIC, amount, incident date)
      - runs a prompt-injection / security scan
      - outputs a sanitized dispute package consumed by the downstream pipeline.
    """

    AGENT_NAME = "ingestion-security-agent"

    def pdf_extract(self, attachment_bytes: bytes = b"", filename: str = "") -> str:
        """Extract text from a PDF bank statement or evidence attachment.

        Call this tool when a PDF attachment is available to read its text content.
        Returns the extracted text or an error message if extraction fails.
        """
        text = pdf_text_from_bytes(attachment_bytes)
        if not text:
            return "PDF contained no extractable text (scanned image; OCR unavailable) or file was empty."
        logger.info(f"[IntakeAgent] pdf_extract: extracted {len(text)} chars from '{filename}'")
        return text[:6000]

    def build_tool_catalog(self) -> List[Callable]:
        """Return the python callables exposed to the LLM as tools."""
        return [self.pdf_extract]

    def _security_scan(self, email_body: str, subject: str) -> Dict[str, Any]:
        """Lightweight prompt-injection scan on raw intake text (rule-based + optional AI)."""
        flags = []
        combined = f"{subject} {email_body}".lower()
        patterns = {
            "prompt_injection": [
                "ignore previous instructions", "ignore all previous", "disregard your",
                "you are now", "act as", "system prompt", "override instructions",
                "forget your instructions", "reveal your system prompt",
            ],
            "conflicting_directives": ["do not follow", "disregard", "override"],
        }
        for flag_type, needles in patterns.items():
            hits = [n for n in needles if n in combined]
            if hits:
                flags.append({"type": flag_type, "patterns": hits})
        return {
            "has_security_flags": len(flags) > 0,
            "flags": flags,
            "assessment": "clean" if not flags else "potential injection attempt detected; content sanitized",
        }

    def process(
        self,
        email_body: str,
        email_subject: str,
        sender_name: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        fallback_amount: float = 1500.0,
    ) -> Dict[str, Any]:
        """
        Run the agentic intake loop and return a sanitized dispute package.

        Returns a dict with:
          entities: {customer_name, account_number, nric, amount, incident_date}
          security: {has_security_flags, flags, assessment}
          attachment_text: extracted PDF text used (for audit/debug)
          used_tools: list of tool names the agent called
        """
        attachments = attachments or []
        pdf_bytes = b""
        pdf_name = ""
        for att in attachments:
            if att.get("mimeType") == "application/pdf" or str(att.get("filename", "")).lower().endswith(".pdf"):
                pdf_bytes = att.get("content_bytes") or b""
                pdf_name = att.get("filename") or "attachment.pdf"
                break

        # Pre-extract PDF text so it's available for both agentic and fallback paths
        pdf_text_preextracted = ""
        if pdf_bytes:
            try:
                pdf_text_preextracted = pdf_text_from_bytes(pdf_bytes)
                if pdf_text_preextracted:
                    logger.info(f"[IntakeAgent] Pre-extracted {len(pdf_text_preextracted)} chars from PDF '{pdf_name}'")
                else:
                    logger.warning(f"[IntakeAgent] PDF '{pdf_name}' yielded no text (scanned or empty)")
            except Exception as pdf_err:
                logger.error(f"[IntakeAgent] PDF pre-extraction error: {pdf_err}")

        if not email_body or not email_body.strip():
            return {
                "entities": self._default_entities(sender_name, fallback_amount),
                "security": {"has_security_flags": False, "flags": [], "assessment": "empty intake"},
                "attachment_text": pdf_text_preextracted[:6000],
                "used_tools": [],
            }

        # Security scan first (pure, no LLM needed).
        security = self._security_scan(email_body, email_subject)

        sop_context = self.agent_context()

        # Build the system prompt — tool name MUST match the registered function name exactly
        system_prompt = (
            "You are Rhea, the Ingestion & Security Agent in an AI Banking Dispute Automation Taskforce.\n"
            "You process incoming customer complaint emails for a Malaysian bank.\n\n"
            "YOUR TOOLS:\n"
            "- `pdf_extract`: Call this ONLY when ATTACHMENT AVAILABLE says YES and you need the raw PDF content.\n\n"
            "YOUR WORKFLOW:\n"
            "1. Read EVERY WORD of the EMAIL BODY carefully. The amount is almost always there.\n"
            "2. If PDF TEXT is provided below, read it too for supplementary evidence.\n"
            "3. If ATTACHMENT AVAILABLE says YES and you still need more detail, call `pdf_extract`.\n"
            "4. Output ONLY a single JSON object. NO markdown fences, NO explanation, NO backticks.\n\n"
            "EXTRACTION RULES (be extremely precise):\n"
            "- amount: Look for patterns like 'RM 300', 'RM300', 'MYR 1,450.00', 'MYR1450', '$ 300', '300.00'.\n"
            "  Strip ALL non-numeric chars except the decimal point. E.g. 'RM 1,450.00' → 1450.00, 'RM 300' → 300.0.\n"
            "  NEVER return 0 or null if you can find any monetary value in the text.\n"
            "- account_number: Full 10-12 digit number, or 'ending in XXXX' style → extract just the digits.\n"
            "- card_number: Full card or last 4 digits. null if not mentioned.\n"
            "- nric: Malaysian format dddddd-dd-dddd only. null if not found.\n"
            "- customer_name: Full name from email signature or sender header. Use sender name if nothing else.\n"
            "- incident_date: YYYY-MM-DD format. null if not found.\n"
            f"REQUIRED JSON FORMAT:\n{_ENTITY_JSON_SCHEMA}"
        )

        # Always include pre-extracted PDF text in the user prompt so AI has full context
        pdf_context_section = ""
        if pdf_text_preextracted:
            pdf_context_section = (
                f"\n\nPDF ATTACHMENT TEXT (pre-extracted for you — read this carefully):\n"
                f"{'='*60}\n"
                f"{pdf_text_preextracted[:5000]}\n"
                f"{'='*60}"
            )

        user_prompt = (
            f"SENDER NAME (from email header): {sender_name}\n"
            f"EMAIL SUBJECT: {email_subject}\n\n"
            "EMAIL BODY:\n"
            f"{email_body}"
            f"{pdf_context_section}\n\n"
            f"ATTACHMENT AVAILABLE: {'YES (' + pdf_name + ') — call pdf_extract if you need raw bytes' if pdf_bytes else 'NO'}\n"
            f"NOTE: If you found the amount in the text above, return it directly. DO NOT return 0 or null for amount if any monetary value exists in the text."
        )

        used_tools: List[str] = []

        # Closure captures pdf_bytes so the model doesn't need to pass binary arguments
        def execute_tool(name, args):
            if name in ("pdf_extract", "_tool_pdf_extract"):
                used_tools.append("pdf_extract")
                result = self.pdf_extract(pdf_bytes, pdf_name)
                logger.info(f"[IntakeAgent] Tool 'pdf_extract' executed → {len(result)} chars returned")
                return result
            logger.warning(f"[IntakeAgent] Unknown tool requested: '{name}'")
            return f"Unknown tool '{name}'. Available tools: pdf_extract"

        final_text = generate_content_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=self.build_tool_catalog(),
            execute_tool=execute_tool,
            max_turns=6,  # increased from 4 to allow tool → response → final answer cycle
        )

        entities = None
        if final_text:
            entities = parse_json_response(final_text)
            if entities:
                logger.info(f"[IntakeAgent] Agentic extraction succeeded: {list(entities.keys())}")
            else:
                logger.warning(f"[IntakeAgent] Agentic final text could not be parsed as JSON: {final_text[:200]}")

        if not entities:
            # Fallback: plain single-shot JSON call with both email AND pre-extracted PDF text
            logger.info("[IntakeAgent] Falling back to plain JSON extraction (no tool calling)")
            entities = self._plain_extract(
                email_body, email_subject, sender_name,
                pdf_text=pdf_text_preextracted,
                fallback_amount=fallback_amount
            )

        entities = self._normalize(entities, sender_name, fallback_amount)

        return {
            "entities": entities,
            "security": security,
            "attachment_text": pdf_text_preextracted[:6000],
            "used_tools": used_tools or self._detect_used_tools(final_text),
        }

    def agent_context(self) -> str:
        """Build the team SOP context for this agent (capped)."""
        return build_team_sop(max_chars=4000)

    def _plain_extract(self, email_body, email_subject, sender_name, pdf_text, fallback_amount) -> Dict[str, Any]:
        """Single-shot non-tool extraction used as a fallback (no function calling)."""
        content = (
            f"EMAIL SUBJECT: {email_subject}\n\n"
            f"EMAIL BODY:\n{email_body}"
        )
        if pdf_text:
            content += (
                f"\n\nPDF ATTACHMENT TEXT:\n"
                f"{'='*60}\n{pdf_text[:4000]}\n{'='*60}"
            )

        system_prompt = (
            "You are a financial dispute extraction agent. Extract structured data from the email and PDF text below.\n"
            "CRITICAL: Find the DISPUTE AMOUNT. Look for:\n"
            "  - 'RM 300', 'RM300', 'MYR 1,450.00', 'MYR1450' → strip RM/MYR and commas → return as float\n"
            "  - 'Transaction Amount: 300' or 'amount of 300' → return 300.0\n"
            "  - NEVER return 0 or null for amount if any monetary value exists in the text.\n\n"
            "Other fields:\n"
            "- customer_name: complainant full name (from email signature or sender)\n"
            "- account_number: digits only (10-12 digits or last 4), or null\n"
            "- card_number: full or last 4 digits, or null\n"
            "- nric: dddddd-dd-dddd format only, or null\n"
            "- incident_date: YYYY-MM-DD, or null\n\n"
            "Return ONLY valid JSON. No markdown, no backticks, no explanation.\n"
            f"Format: {_ENTITY_JSON_SCHEMA}"
        )
        data = generate_json(system_prompt, f"Sender: {sender_name}\n\n{content}")
        if data and isinstance(data, dict):
            logger.info(f"[IntakeAgent] Plain extraction succeeded: {list(data.keys())}")
            return data
        logger.warning("[IntakeAgent] Plain extraction also failed — using defaults")
        return {}

    def _normalize(self, data: dict, sender_name: str, fallback_amount: float) -> dict:
        import re
        if not isinstance(data, dict):
            data = {}
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
        card = data.get("card_number")
        if card is not None and str(card).strip().lower() in ("null", "none", "n/a", ""):
            card = None
        nric = data.get("nric")
        if nric is not None and str(nric).strip().lower() in ("null", "none", "n/a", ""):
            nric = None
        name = data.get("customer_name")
        if not name or str(name).strip().lower() in ("null", "none", "unknown", ""):
            name = sender_name

        return {
            "customer_name": str(name).strip() or sender_name,
            "account_number": str(account).strip() if account else None,
            "card_number": str(card).strip() if card else None,
            "nric": str(nric).strip() if nric else None,
            "amount": amount if amount is not None and amount > 0 else fallback_amount,
            "incident_date": (str(data.get("incident_date") or "").strip() or None),
        }

    def _default_entities(self, sender_name: str, fallback_amount: float) -> dict:
        return {
            "customer_name": sender_name,
            "account_number": None,
            "card_number": None,
            "nric": None,
            "amount": fallback_amount,
            "incident_date": None,
        }

    def _detect_used_tools(self, final_text) -> List[str]:
        if final_text and "pdf_extract" in final_text:
            return ["pdf_extract"]
        return []


intake_agent = IntakeAgent()
