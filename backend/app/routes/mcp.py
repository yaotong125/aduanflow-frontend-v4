import logging
from fastapi import APIRouter
from typing import Dict, Any, Optional
from backend.app.services.verification_service import verification_service
from backend.app.services.gmail_sync_agent import gmail_sync_agent
from backend.app.services.resolution_service import resolution_service
from backend.app.services.ledger_service import ledger_service

logger = logging.getLogger("aduanflow")
router = APIRouter(prefix="/api/mcp", tags=["Model Context Protocol"])

@router.get("/tools")
def list_mcp_tools():
    """
    Expose Model Context Protocol (MCP) tool declarations for AI agents.
    Complies with Anthropic/OpenAI Model Context Protocol spec.
    """
    return {
        "mcp_version": "1.0.0",
        "tools": [
            {
                "name": "verify_banking_evidence",
                "description": "Cross-reference dispute parameters against core banking logs, switch journals, ATM records, and CRM.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "description": "Dispute amount in MYR"},
                        "category": {"type": "string", "description": "Dispute category (e.g. UNAUTHORIZED_TRANSACTION)"},
                        "email_body": {"type": "string", "description": "Customer complaint body text"}
                    },
                    "required": ["amount", "category"]
                }
            },
            {
                "name": "query_core_ledger",
                "description": "Fetch raw transaction ledger logs for an account number.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_number": {"type": "string"}
                    },
                    "required": ["account_number"]
                }
            },
            {
                "name": "gmail_poll_unread",
                "description": "Query the connected Gmail complaints mailbox for unread dispute emails and pipe them through the 5-stage AI dispute pipeline.",
                "input_schema": {"type": "object", "properties": {}}
            },
            {
                "name": "post_journal_entry",
                "description": "Generate a double-entry GL journal voucher (JE-2026-XXXX) for a credit reversal or provisional credit.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "amount": {"type": "number", "description": "Dispute amount in MYR"},
                        "category": {"type": "string", "description": "Dispute category"}
                    },
                    "required": ["case_id", "amount", "category"]
                }
            }
        ]
    }

@router.get("/gmail/poll")
def gmail_poll():
    """
    Convenience endpoint for the Email MCP: trigger an immediate Gmail sync cycle.
    Returns synced case IDs or the reason the mailbox is inactive.
    """
    result = gmail_sync_agent.run_sync_cycle()
    return {
        "tool": "gmail_poll_unread",
        "status": result.get("status", "error"),
        "result": result
    }

@router.post("/execute")
def execute_mcp_tool(payload: Dict[str, Any]):
    """
    Execute an MCP Tool call directly from an AI agent.
    """
    tool_name = payload.get("name")
    arguments = payload.get("arguments", {})

    logger.info(f"[MCP] Executing MCP Tool: {tool_name} with args: {arguments}")

    if tool_name == "verify_banking_evidence":
        result = verification_service.verify_case(arguments)
        return {
            "status": "success",
            "tool_name": tool_name,
            "result": result
        }
    elif tool_name == "gmail_poll_unread":
        result = gmail_sync_agent.run_sync_cycle()
        return {
            "status": "success" if result.get("status") in {"success", "inactive"} else "error",
            "tool_name": tool_name,
            "result": result
        }
    elif tool_name == "post_journal_entry":
        case_id = arguments.get("case_id")
        amount = arguments.get("amount", 0.0)
        category = arguments.get("category", "")
        if not case_id:
            return {"status": "error", "tool_name": tool_name, "message": "Missing case_id"}
        result = resolution_service.resolve_financials(case_id, float(amount), category)
        if result is None:
            return {"status": "error", "tool_name": tool_name, "message": "Invalid amount"}
        return {"status": "success", "tool_name": tool_name, "result": result}
    elif tool_name == "query_core_ledger":
        acc = arguments.get("account_number", "UNKNOWN")
        amount = arguments.get("amount", 0.0)
        result = ledger_service.query_core_ledger(acc, float(amount))
        return {
            "status": "success",
            "tool_name": tool_name,
            "result": result
        }

    return {"status": "error", "message": f"Unknown MCP tool: {tool_name}"}
