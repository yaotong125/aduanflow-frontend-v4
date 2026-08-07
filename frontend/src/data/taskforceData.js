import { DISPUTE_CATEGORIES, mockCases } from './mockData';

export const TASKFORCE_TEAM = {
  name: 'AI Banking Dispute Automation Taskforce',
  tagline: 'Policy-aware multi-expert command layer for high-risk banking disputes.',
  mission:
    'Unify fraud recovery, dispute evidence review, regulatory escalation, and customer redress into one coordinated operating model.',
  operatingCadence: 'Always-on triage with 30-minute escalation pack assembly for priority cases.',
  members: [
    {
      name: 'Aegis',
      role: 'Team Lead Orchestrator',
      focus: 'Monitors dispute queue health, routes cases to specialist squads, and keeps every case within BNM SLA.',
      specialty: 'Cross-squad orchestration',
      accent: 'from-blue-600 to-indigo-600',
    },
    {
      name: 'Rhea (Security)',
      role: 'Ingestion & PII Security Specialist',
      focus: 'Connects to complaints mailbox (Gmail OAuth 2.0), applies PDF OCR extraction, and enforces Fernet PII encryption at rest.',
      specialty: 'Email intake & PII encryption',
      accent: 'from-red-500 to-rose-600',
    },
    {
      name: 'Nadia (Compliance)',
      role: 'Dispute Classifier & BNM Compliance Strategist',
      focus: 'Categorizes disputes across 7 PayNet categories, calculates 5-day / 20-day BNM SLAs, and stamps governance metadata.',
      specialty: 'BNM policy governance & SLA assignment',
      accent: 'from-violet-600 to-purple-600',
    },
    {
      name: 'Faris (Verification)',
      role: 'MCP Verification & Resolution Analyst',
      focus: 'Cross-references core banking logs using MCP, detects location & threshold anomalies, and posts automated journal entries.',
      specialty: 'Core MCP verification & financial resolution',
      accent: 'from-amber-500 to-orange-600',
    },
    {
      name: 'Maya (Comms)',
      role: 'Customer Communications & Dashboard Specialist',
      focus: 'Generates BNM-compliant resolution notices and embeds FMOS 6-month right of referral disclosures for claims ≤ RM 250,000.',
      specialty: 'FMOS disclosures & dashboard sync',
      accent: 'from-cyan-600 to-teal-600',
    },
  ],
  squads: [
    {
      name: 'Fraud Strike Cell',
      lead: 'Rhea',
      backup: 'Faris',
      objective: 'Contain exposure, validate fraud signals, and secure fast provisional outcomes.',
      handles: [
        'unauthorized_transactions',
        'atm_debit_card_disputes',
        'emoney_digital_payment_disputes',
      ],
    },
    {
      name: 'Billing and Reconciliation Desk',
      lead: 'Idris',
      backup: 'Faris',
      objective: 'Resolve statement variances, calculation errors, and reconciliation breaks.',
      handles: ['billing_errors', 'loan_financing_disputes'],
    },
    {
      name: 'Conduct and Suitability Panel',
      lead: 'Nadia',
      backup: 'Sentinel',
      objective: 'Handle high-sensitivity conduct disputes, product suitability, and regulated appeals.',
      handles: ['mis_selling_claims', 'insurance_takaful_claims'],
    },
  ],
  playbooks: [
    {
      name: 'Urgent fraud containment',
      trigger: 'Unauthorized transfer, card fraud, or suspicious cash-out with high urgency or amount above RM 1,000.',
      steps: [
        'Freeze exposure and validate device / IP anomalies.',
        'Assemble evidence pack with transaction, CRM, and geo markers.',
        'Prepare provisional credit and security advisory draft.',
      ],
    },
    {
      name: 'Suitability and conduct escalation',
      trigger: 'Mis-selling, policy mismatch, or complaints with regulatory escalation language.',
      steps: [
        'Compare customer profile against product risk or policy conditions.',
        'Flag disclosure gaps, recording reviews, and escalation obligations.',
        'Generate reviewer-ready compliance brief and redress options.',
      ],
    },
    {
      name: 'Statement and servicing correction',
      trigger: 'Billing errors, duplicate charges, loan interest discrepancies, or failed settlement postings.',
      steps: [
        'Reconcile statement entries against system-of-record transactions.',
        'Quantify financial delta and identify correct remediation path.',
        'Draft customer response with corrected calculations and timelines.',
      ],
    },
  ],
  commandPrompts: [
    'Show taskforce coverage',
    'Which squad owns escalations?',
    'List high-risk disputes for the taskforce',
    'Prepare a remediation summary for manual review cases',
  ],
};

const CATEGORY_SQUAD_MAP = Object.fromEntries(
  TASKFORCE_TEAM.squads.flatMap((squad) =>
    squad.handles.map((category) => [category, { squad: squad.name, lead: squad.lead, objective: squad.objective }])
  )
);

const STATUS_PRIORITY = {
  MANUAL_REVIEW: 4,
  PENDING: 3,
  FAIL: 2,
  PASS: 1,
  FINANCIALLY_RESOLVED: 1,
};

function resolveSquad(category) {
  return (
    CATEGORY_SQUAD_MAP[category] || {
      squad: 'Core Resolution Desk',
      lead: 'Aegis',
      objective: 'Coordinate the right specialists and maintain queue momentum.',
    }
  );
}

function getMissionReason(caseItem) {
  return (
    caseItem.verification?.manualReviewReason ||
    caseItem.classification?.rationale ||
    'Requires coordinated dispute review and response drafting.'
  );
}

function getRecommendedAction(caseItem, squad) {
  if (caseItem.status === 'MANUAL_REVIEW') {
    return `Escalate to ${squad.squad} and prepare a reviewer-ready evidence pack.`;
  }

  if (caseItem.status === 'PENDING') {
    return `Route into ${squad.squad} for accelerated triage and acknowledgement coverage.`;
  }

  if (caseItem.status === 'FAIL') {
    return 'Validate decline reasoning, confirm policy basis, and harden customer messaging.';
  }

  if (caseItem.amount >= 5000 || caseItem.urgency === 'high') {
    return 'Keep the case under taskforce watch until the customer outcome is confirmed.';
  }

  return 'Monitor for drift and keep the response pack audit-ready.';
}

export function deriveTaskforceMissions(cases = mockCases) {
  return cases
    .map((caseItem) => {
      const squad = resolveSquad(caseItem.category);
      const categoryMeta = DISPUTE_CATEGORIES[caseItem.category];
      const priorityScore =
        (STATUS_PRIORITY[caseItem.status] || 0) * 100 +
        (caseItem.urgency === 'high' ? 30 : caseItem.urgency === 'medium' ? 15 : 5) +
        Math.min(caseItem.amount / 100, 60);

      return {
        caseId: caseItem.id,
        customerName: caseItem.customerName,
        category: categoryMeta?.label || caseItem.category,
        status: caseItem.status,
        urgency: caseItem.urgency,
        amount: caseItem.amount,
        squad: squad.squad,
        owner: squad.lead,
        reason: getMissionReason(caseItem),
        recommendedAction: getRecommendedAction(caseItem, squad),
        priority: Math.round(priorityScore),
      };
    })
    .filter(
      (mission) =>
        mission.status === 'MANUAL_REVIEW' ||
        mission.status === 'PENDING' ||
        mission.urgency === 'high' ||
        mission.amount >= 5000
    )
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 6);
}

export function buildTaskforceOverview(cases = mockCases) {
  const missions = deriveTaskforceMissions(cases);
  const manualEscalations = cases.filter((caseItem) => caseItem.status === 'MANUAL_REVIEW').length;
  const straightThroughRate = Math.round(
    cases.length ? (cases.filter((caseItem) => caseItem.status === 'PASS').length / cases.length) * 100 : 0
  );
  const highValueExposure = cases
    .filter((caseItem) => caseItem.amount >= 5000 || caseItem.status === 'MANUAL_REVIEW')
    .reduce((sum, caseItem) => sum + caseItem.amount, 0);

  const squads = TASKFORCE_TEAM.squads.map((squad) => {
    const squadCases = cases.filter((caseItem) => squad.handles.includes(caseItem.category));
    const activeCount = squadCases.filter(
      (caseItem) => caseItem.status === 'MANUAL_REVIEW' || caseItem.status === 'PENDING' || caseItem.urgency === 'high'
    ).length;

    return {
      ...squad,
      caseCount: squadCases.length,
      activeCount,
      highValueCount: squadCases.filter((caseItem) => caseItem.amount >= 5000).length,
    };
  });

  return {
    team: TASKFORCE_TEAM,
    summary: {
      activeMissionCount: missions.length,
      manualEscalations,
      highValueExposure,
      straightThroughRate,
      totalCases: cases.length,
      priorityCoverage: cases.filter((caseItem) => caseItem.urgency === 'high').length,
    },
    members: TASKFORCE_TEAM.members,
    squads,
    missions,
    playbooks: TASKFORCE_TEAM.playbooks,
    commandPrompts: TASKFORCE_TEAM.commandPrompts,
  };
}
