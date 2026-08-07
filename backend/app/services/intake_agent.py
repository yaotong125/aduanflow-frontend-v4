import logging
import json
from typing import Dict, Any, Optional, Callable, List

from backend.app.services.gemini_client import generate_content_with_tools, parse_json_response, generate_json
from backend.app.services.pdf_extractor import pdf_text_from_bytes
from backend.app.services.plugin_context import build_team_sop

logger = logging.getLogger("aduanflow")


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
        """Extract text from a PDF attachment (bank statement or evidence document)."""
        text = pdf_text_from_bytes(attachment_bytes)
        if not text:
            return "PDF contained no extractable text (may be a scanned image; OCR unavailable) or file was empty."
        return text[:6000]

    def build_tool_catalog(self) -> List[Callable]:
        """Return the python callables exposed to the LLM as tools."""
        return [self.pdf_extract]

    def _execute_tool(self, name: str, args: dict) -> str:
        """Dispatch an LLM-requested tool call to the matching implementation."""
        if name in ("pdf_extract", "_tool_pdf_extract"):  # accept both names defensively
            pdf_bytes = args.get("attachment_bytes") or args.get("attachment") or b""
            filename = args.get("filename", "")
            return self.pdf_extract(pdf_bytes, filename)
        return f"Unknown tool '{name}'"

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

        if not email_body or not email_body.strip():
            return {
                "entities": self._default_entities(sender_name, fallback_amount),
                "security": {"has_security_flags": False, "flags": [], "assessment": "empty intake"},
                "attachment_text": "",
                "used_tools": [],
            }

        # Security scan first (pure, no LLM needed).
        security = self._security_scan(email_body, email_subject)

        # Agentic extraction loop with the pdf_extract tool available.
        system_prompt = (
            "You are Rhea, the Ingestion & Security Agent in an AI Banking Dispute Automation Taskforce.\n"
            "You process incoming customer complaint emails for a bank.\n"
            "Your job:\n"
            "1. Read the complaint email body.\n"
            "2. If there is a PDF attachment available, call the `_tool_pdf_extract` tool to read it.\n"
            "3. Extract structured entities accurately.\n"
            "Use the team SOP as your operating context.\n"
            f"\n{self.agent_context()}\n"
            "IMPORTANT INSTRUCTIONS:\n"
            "Think step by step before outputting JSON. Ensure you extract the exact amount without currency symbols, just the number.\n"
            "Finally respond with ONLY a single JSON object (no markdown, no backticks):\n"
            '{"customer_name": "<name or null>", '
            '"account_number": "<full account number digits or null>", '
            '"card_number": "<full card number or 4-digit ending, or null>", '
            '"nric": "<dddddd-dd-dddd or null>", '
            '"amount": <number or null>, '
            '"incident_date": "<YYYY-MM-DD or null>", '
            '"used_tools": ["<tool names called>"]}'
        )
        user_prompt = (
            f"SENDER (from email header): {sender_name}\n"
            f"EMAIL SUBJECT: {email_subject}\n\n"
            "EMAIL BODY:\n"
            f"{email_body}\n\n"
            f"ATTACHMENT AVAILABLE: {'YES (' + pdf_name + ')' if pdf_bytes else 'NO'}\n"
            f"FALLBACK AMOUNT IF NOT FOUND IN TEXT: {fallback_amount}"
        )

        used_tools: List[str] = []
        # We need to pass pdf_bytes into the tool call. The model cannot pass binary;
        # we make it available to the tool via closure.
        def execute_tool(name, args):
            if name in ("pdf_extract", "_tool_pdf_extract"):  # accept both names defensively
                used_tools.append("pdf_extract")
                # Force our captured bytes regardless of model-supplied dummy args.
                return self.pdf_extract(pdf_bytes, pdf_name)
            return f"Unknown tool '{name}'"

        final_text = generate_content_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=self.build_tool_catalog(),
            execute_tool=execute_tool,
            max_turns=4,
        )

        entities = None
        if final_text:
            entities = parse_json_response(final_text)
        if not entities:
            # Fallback: plain single-shot JSON call (no tools) so the pipeline never hard-crashes.
            entities = self._plain_extract(email_body, email_subject, sender_name, pdf_text=(pdf_text_from_bytes(pdf_bytes) if pdf_bytes else ""), fallback_amount=fallback_amount)

        entities = self._normalize(entities, sender_name, fallback_amount)

        return {
            "entities": entities,
            "security": security,
            "attachment_text": pdf_text_from_bytes(pdf_bytes)[:6000] if pdf_bytes else "",
            "used_tools": used_tools or self._detect_used_tools(final_text),
        }

    def agent_context(self) -> str:
        """Build the team SOP context for this agent (capped)."""
        return build_team_sop(max_chars=4000)

    def _plain_extract(self, email_body, email_subject, sender_name, pdf_text, fallback_amount) -> Dict[str, Any]:
        """Single-shot non-tool extraction used as a fallback (no function calling)."""
        content = email_body
        if pdf_text:
            content += "\n\n--- PDF ATTACHMENT TEXT ---\n" + pdf_text
        system_prompt = (
            "You are an OCR/document-parsing agent for a banking dispute automation system.\n"
            "Extract the following fields from the complaint email and any attached document text.\n"
            "Think step-by-step and carefully identify numbers and names. Remove any 'RM' or '$' from amount.\n"
            "Return ONLY JSON (no markdown formatting or backticks).\n"
            "- customer_name: full name of complainant\n"
            "- account_number: full account number digits, or null\n"
            "- card_number: full card number or 4-digit ending, or null\n"
            "- nric: dddddd-dd-dddd, or null\n"
            "- amount: numeric MYR, no symbol (e.g. 620.00), or null\n"
            "- incident_date: YYYY-MM-DD, or null\n"
            'Response format: {"customer_name":..., "account_number":..., "card_number":..., "nric":..., "amount":..., "incident_date":...}'
        )
        data = generate_json(system_prompt, f"Sender: {sender_name}\nSubject: {email_subject}\n\n{content}")
        return data if isinstance(data, dict) else {}

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
