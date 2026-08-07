import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from backend.app.models.case import Case

logger = logging.getLogger(__name__)

_env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=_env_path)

_api_key = os.getenv("GEMINI_API_KEY")

try:
    from google import genai as _genai
    if not _api_key:
        raise ValueError("GEMINI_API_KEY is missing or empty")
    _gemini_client = _genai.Client(api_key=_api_key)
    _gemini_available = True
    logger.info("[Taskforce] Gemini client initialised successfully")
except Exception as e:
    logger.error(f"[Taskforce] Gemini init failed: {e}")
    _gemini_available = False
    _gemini_client = None

_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def get_llm_agent_brief(agent_name: str, agent_role: str, case: "Case") -> str:
    """Generate an LLM-powered brief for a specific agent and case."""
    if not _gemini_available:
        return f"{agent_name} is reviewing this case."
    try:
        prompt = (
            f"You are {agent_name}, {agent_role} in an AI banking dispute taskforce.\n"
            f"Case ID: {case.id}\n"
            f"Customer: {case.customer_name}\n"
            f"Category: {case.category}\n"
            f"Amount: RM {case.amount:,.2f}\n"
            f"Status: {case.status}\n"
            f"Urgency: {case.urgency}\n"
            f"Description: {getattr(case, 'description', 'N/A')}\n\n"
            f"In 2-3 sentences, provide your expert assessment and recommended next action for this case."
        )
        response = _gemini_client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"[Taskforce] Gemini brief failed for {agent_name}: {e}")
        return f"{agent_name} is reviewing this case."

TASKFORCE_MEMBERS: List[Dict[str, str]] = [
    {
        'name': 'Aegis',
        'role': 'Team Lead Orchestrator',
        'focus': 'Monitors dispute queue health, routes cases to specialist squads, and keeps every case within BNM SLA.',
        'specialty': 'Cross-squad orchestration',
        'accent': 'from-blue-600 to-indigo-600',
    },
    {
        'name': 'Rhea (Security)',
        'role': 'Ingestion & PII Security Specialist',
        'focus': 'Connects to complaints mailbox (Gmail OAuth 2.0), applies PDF OCR extraction, and enforces Fernet PII encryption at rest.',
        'specialty': 'Email intake & PII encryption',
        'accent': 'from-red-500 to-rose-600',
    },
    {
        'name': 'Nadia (Compliance)',
        'role': 'Dispute Classifier & BNM Compliance Strategist',
        'focus': 'Categorizes disputes across 7 PayNet categories, calculates 5-day / 20-day BNM SLAs, and stamps governance metadata.',
        'specialty': 'BNM policy governance & SLA assignment',
        'accent': 'from-violet-600 to-purple-600',
    },
    {
        'name': 'Faris (Verification)',
        'role': 'MCP Verification & Resolution Analyst',
        'focus': 'Cross-references core banking logs using MCP, detects location & threshold anomalies, and posts automated journal entries.',
        'specialty': 'Core MCP verification & financial resolution',
        'accent': 'from-amber-500 to-orange-600',
    },
    {
        'name': 'Maya (Comms)',
        'role': 'Customer Communications & Dashboard Specialist',
        'focus': 'Generates BNM-compliant resolution notices and embeds FMOS 6-month right of referral disclosures for claims ≤ RM 250,000.',
        'specialty': 'FMOS disclosures & dashboard sync',
        'accent': 'from-cyan-600 to-teal-600',
    },
]

TASKFORCE_SQUADS: List[Dict[str, Any]] = [
    {
        'name': 'Fraud Strike Cell',
        'lead': 'Rhea',
        'backup': 'Faris',
        'objective': 'Contain exposure, validate fraud signals, and land fast customer-safe outcomes.',
        'handles': [
            'unauthorized_transactions',
            'atm_debit_card_disputes',
            'emoney_digital_payment_disputes',
        ],
    },
    {
        'name': 'Billing and Reconciliation Desk',
        'lead': 'Idris',
        'backup': 'Faris',
        'objective': 'Resolve statement mismatches, servicing errors, and reconciliation gaps.',
        'handles': ['billing_errors', 'loan_financing_disputes'],
    },
    {
        'name': 'Conduct and Suitability Panel',
        'lead': 'Nadia',
        'backup': 'Sentinel',
        'objective': 'Review suitability, disclosures, policy fairness, and regulated complaint risk.',
        'handles': ['mis_selling_claims', 'insurance_takaful_claims'],
    },
]

CATEGORY_LABELS = {
    'unauthorized_transactions': 'Unauthorized Transactions',
    'billing_errors': 'Billing Errors',
    'mis_selling_claims': 'Mis-selling Claims',
    'atm_debit_card_disputes': 'ATM / Debit Card Disputes',
    'insurance_takaful_claims': 'Insurance / Takaful Claims',
    'loan_financing_disputes': 'Loan / Financing Disputes',
    'emoney_digital_payment_disputes': 'E-money / Digital Payment',
}

COMMAND_PROMPTS = [
    'Show taskforce coverage',
    'Which squad owns escalations?',
    'List high-risk disputes for the taskforce',
    'Prepare a remediation summary for manual review cases',
]

PLAYBOOKS = [
    {
        'name': 'Urgent fraud containment',
        'trigger': 'Unauthorized transfer, card fraud, or suspicious cash-out with high urgency or amount above RM 1,000.',
        'steps': [
            'Freeze exposure and validate device / IP anomalies.',
            'Assemble evidence pack with transaction, CRM, and geo markers.',
            'Prepare provisional credit and security advisory draft.',
        ],
    },
    {
        'name': 'Suitability and conduct escalation',
        'trigger': 'Mis-selling, policy mismatch, or complaints with regulatory escalation language.',
        'steps': [
            'Compare customer profile against product risk or policy conditions.',
            'Flag disclosure gaps, recording reviews, and escalation obligations.',
            'Generate reviewer-ready compliance brief and redress options.',
        ],
    },
    {
        'name': 'Statement and servicing correction',
        'trigger': 'Billing errors, duplicate charges, loan interest discrepancies, or failed settlement postings.',
        'steps': [
            'Reconcile statement entries against system-of-record transactions.',
            'Quantify financial delta and identify the correct remediation path.',
            'Draft customer response with corrected calculations and timelines.',
        ],
    },
]

CATEGORY_SQUAD_MAP = {
    category: {
        'squad': squad['name'],
        'lead': squad['lead'],
        'objective': squad['objective'],
    }
    for squad in TASKFORCE_SQUADS
    for category in squad['handles']
}

STATUS_PRIORITY = {
    'MANUAL_REVIEW': 4,
    'FAIL': 2,
    'PASS': 1,
}


def resolve_squad(category: str) -> Dict[str, str]:
    return CATEGORY_SQUAD_MAP.get(
        category,
        {
            'squad': 'Core Resolution Desk',
            'lead': 'Aegis',
            'objective': 'Coordinate the right specialists and maintain queue momentum.',
        },
    )


def mission_reason(case: Case) -> str:
    verification = case.verification or {}
    classification = case.classification or {}
    return (
        verification.get('manualReviewReason')
        or classification.get('rationale')
        or 'Requires coordinated dispute review and response drafting.'
    )


def recommended_action(case: Case, squad: Dict[str, str]) -> str:
    if case.status == 'MANUAL_REVIEW':
        return f"Escalate to {squad['squad']} and prepare a reviewer-ready evidence pack."
    if case.status == 'FAIL':
        return 'Validate decline reasoning, confirm policy basis, and harden customer messaging.'
    if case.amount >= 5000 or case.urgency == 'high':
        return 'Keep the case under taskforce watch until the customer outcome is confirmed.'
    return 'Monitor for drift and keep the response pack audit-ready.'


def build_mission(case: Case) -> Dict[str, Any]:
    squad = resolve_squad(case.category)
    priority_score = (STATUS_PRIORITY.get(case.status, 0) * 100) + (
        30 if case.urgency == 'high' else 15 if case.urgency == 'medium' else 5
    ) + min(case.amount / 100, 60)

    return {
        'caseId': case.id,
        'customerName': case.customer_name,
        'category': CATEGORY_LABELS.get(case.category, case.category),
        'status': case.status,
        'urgency': case.urgency,
        'amount': round(case.amount, 2),
        'squad': squad['squad'],
        'owner': squad['lead'],
        'reason': mission_reason(case),
        'recommendedAction': recommended_action(case, squad),
        'priority': round(priority_score),
    }


class TaskforceService:
    def build_overview(self, cases: List[Case]) -> Dict[str, Any]:
        cases = list(cases or [])

        missions = [
            build_mission(case)
            for case in cases
            if case.status in {'MANUAL_REVIEW'} or case.urgency == 'high' or case.amount >= 5000
        ]
        missions.sort(key=lambda mission: mission['priority'], reverse=True)
        missions = missions[:8]

        manual_escalations = len([case for case in cases if case.status == 'MANUAL_REVIEW'])
        straight_through_rate = round(
            (len([case for case in cases if case.status == 'PASS']) / len(cases)) * 100
        ) if cases else 0
        high_value_exposure = round(
            sum(case.amount for case in cases if case.amount >= 5000 or case.status == 'MANUAL_REVIEW'),
            2,
        )

        squads: List[Dict[str, Any]] = []
        for squad in TASKFORCE_SQUADS:
            squad_cases = [case for case in cases if case.category in squad['handles']]
            active_count = len(
                [
                    case
                    for case in squad_cases
                    if case.status in {'MANUAL_REVIEW'} or case.urgency == 'high'
                ]
            )
            squads.append(
                {
                    **squad,
                    'caseCount': len(squad_cases),
                    'activeCount': active_count,
                    'highValueCount': len([case for case in squad_cases if case.amount >= 5000]),
                }
            )

        return {
            'team': {
                'name': 'AI Banking Dispute Automation Taskforce',
                'tagline': 'Policy-aware multi-expert command layer for high-risk banking disputes.',
                'mission': 'Unify fraud recovery, dispute evidence review, regulatory escalation, and customer redress into one coordinated operating model.',
                'operatingCadence': 'Always-on triage with 30-minute escalation pack assembly for priority cases.',
            },
            'summary': {
                'activeMissionCount': len(missions),
                'manualEscalations': manual_escalations,
                'highValueExposure': high_value_exposure,
                'straightThroughRate': straight_through_rate,
                'totalCases': len(cases),
                'priorityCoverage': len([case for case in cases if case.urgency == 'high']),
            },
            'members': TASKFORCE_MEMBERS,
            'squads': squads,
            'missions': missions,
            'playbooks': PLAYBOOKS,
            'commandPrompts': COMMAND_PROMPTS,
        }


taskforce_service = TaskforceService()
