"""
AduanFlow AI — MCP Server (stdio transport for CodeBuddy/WorkBuddy)

Exposes 4 tools that proxy to the FastAPI backend running at http://127.0.0.1:8000.
The backend must be running for tools to work.
"""
import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("aduanflow-mcp")

BACKEND_URL = os.getenv("ADUANFLOW_BACKEND_URL", "http://127.0.0.1:8000")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("mcp package not installed. Run: pip install mcp")
    sys.exit(1)

mcp = FastMCP(
    "AduanFlow AI — Banking Dispute MCP",
    instructions=(
        "AduanFlow AI dispute automation MCP tools. "
        "Use verify_banking_evidence to cross-check a dispute against core banking. "
        "Use query_core_ledger to fetch account ledger records. "
        "Use gmail_poll_unread to poll the Gmail complaints mailbox. "
        "Use post_journal_entry to post a financial resolution journal entry."
    ),
)


def _call_backend(tool_name: str, arguments: dict) -> dict:
    """POST to the backend /api/mcp/execute and return the JSON response."""
    import urllib.request
    import urllib.error

    url = f"{BACKEND_URL}/api/mcp/execute"
    payload = json.dumps({"name": tool_name, "arguments": arguments}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"Backend unreachable at {BACKEND_URL}: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def verify_banking_evidence(amount: float, category: str, email_body: str = "") -> str:
    """Cross-reference a banking dispute against core banking logs, ATM journals, and CRM via MCP.

    Args:
        amount: Dispute amount in MYR
        category: Dispute category (unauthorized_transactions, billing_errors, mis_selling_claims,
                  atm_debit_card_disputes, insurance_takaful_claims, loan_financing_disputes,
                  emoney_digital_payment_disputes)
        email_body: The customer complaint text
    """
    result = _call_backend("verify_banking_evidence", {
        "amount": amount,
        "category": category,
        "email_body": email_body,
    })
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def query_core_ledger(account_number: str, amount: float = 0.0) -> str:
    """Fetch real transaction ledger records for an account number from the dispute case database.

    Args:
        account_number: The bank account number to query
        amount: Optional amount to cross-check
    """
    result = _call_backend("query_core_ledger", {
        "account_number": account_number,
        "amount": amount,
    })
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def gmail_poll_unread() -> str:
    """Poll the connected Gmail complaints mailbox for unread dispute emails and process them through the 5-stage AI pipeline."""
    result = _call_backend("gmail_poll_unread", {})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def post_journal_entry(case_id: str, amount: float, category: str) -> str:
    """Generate a double-entry GL journal voucher (JE-2026-XXXX) for a credit reversal or provisional credit.

    Args:
        case_id: The dispute case ID (e.g. DISP-2026-00124)
        amount: Amount in MYR
        category: Dispute category
    """
    result = _call_backend("post_journal_entry", {
        "case_id": case_id,
        "amount": amount,
        "category": category,
    })
    return json.dumps(result, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    logger.info(f"AduanFlow MCP server starting. Backend: {BACKEND_URL}")
    mcp.run(transport="stdio")
