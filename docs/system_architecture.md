# AduanFlow AI — System Architecture

> Banking Dispute Automation Pipeline · PayNet / BNM-Compliant · Tencent Cloud x UTM Hackathon 2026

## 1. System Overview

AduanFlow AI is a multi-agent banking dispute automation platform. It ingests customer complaints (via Gmail / manual intake), runs them through a 5-stage agentic pipeline, and resolves verified cases straight-through while flagging anomalies for human review — all under Bank Negara Malaysia (BNM) complaint-handling SLAs and FMOS redress disclosure requirements.

```
        ┌─────────────────────────────────────────────────────────────────┐
        │                      EXPERT TEAM (CodeBuddy/WorkBuddy)          │
        │   Team Lead ── Rhea ── Nadia ── Faris ── Maya                  │
        │      (orchestrator)   (intake)  (classify) (verify) (comms)     │
        └───────────────┬──────────────────────────────┬──────────────────┘
                        │   MCP (Model Context Protocol) │
        ┌───────────────▼──────────────────────────────▼──────────────────┐
        │                     FASTAPI BACKEND  (port 8000)                 │
        │                                                                  │
        │   /api/mcp/*          /api/cases  /api/audit  /api/intake        │
        │   /api/taskforce      /api/copilot  /api/settings               │
        │   /api/webhooks/*     /api/db-status                            │
        │                                                                  │
        │   ┌─────────────┐   ┌──────────────┐   ┌─────────────────────┐  │
        │   │ 5-STAGE      │   │ AI SERVICES  │   │ MCP SERVICE LAYER    │  │
        │   │ PIPELINE     │   │  Gemini 2.x  │   │  gmail_poll_unread   │  │
        │   │ intake→...   │   │  (with rule  │   │  verify_banking_     │  │
        │   │ →comms       │   │   fallback)  │   │   evidence           │  │
        │   └──────┬───────┘   └──────┬───────┘   │  query_core_ledger   │  │
        │          │                  │           │  post_journal_entry  │  │
        │          ▼                  ▼           └──────────┬───────────┘  │
        │   ┌───────────────────────────────┐  Gmail API + SMTP           │
        │   │   SQLModel ORM ── Case, Audit  │◄───────── gmail_sync_agent │
        │   └───────────────┬───────────────┘                             │
        │                   │  SQLite / PostgreSQL / MySQL (auto-fallback) │
        └───────────────────┼─────────────────────────────────────────────┘
                            │
        ┌───────────────────▼─────────────────────────────────────────────┐
        │                   REACT FRONTEND  (Vite)                        │
        │   Dashboard · CaseList · CaseDetail · ManualReview · AuditLog    │
        │   Copilot · TaskforceControlCenter · Settings · Notifications    │
        └──────────────────────────────────────────────────────────────────┘
```

## 2. Core Pipeline — the 5-Stage Agentic Flow

Every complaint runs through `IntakeService.process_incoming_complaint()` (`backend/app/services/intake_service.py`).

| Stage | Agent | Service | What it does |
|---|---|---|---|
| 1. Intake & Security | Rhea | `intake_service.py` + `encryption_service.py` + `gmail_sync_agent.py` | Extract PII from email/attachment; encrypt NRIC, account no., amount at rest (Fernet AES-256); build OCR metadata |
| 2. Classification | Nadia | `classification_service.py` | Categorize into 7 PayNet dispute types; set urgency + BNM SLA (5/20 working days); stamp governance metadata |
| 3. Core Verification (MCP) | Faris | `verification_service.py` | Cross-reference against core banking ledger via MCP; output **PASS / FAIL / MANUAL_REVIEW**; >RM 5,000 or location anomaly → MANUAL_REVIEW |
| 4. Financial Resolution | Faris | `resolution_service.py` | PASS cases: post provisional credit / reversal, generate JE-2026-XXXX journal entry, status → FINANCIALLY_RESOLVED |
| 5. Compliant Comms | Maya | `communication_service.py` | Generate BNM/FMOS-compliant resolution email; real dispatch via SMTP or Gmail API |
| — | — | `audit` (models + routes) | Append full audit trail to every case |

### 2.1 Classification logic (`classification_service.py`)
Rule-based keyword matching over 7 categories + BNM SLA stamping:
- `unauthorized_transactions`, `atm_debit_card_disputes` → **high** urgency, 5 working days
- `billing_errors`, `mis_selling_claims`, `insurance_takaful_claims`, `loan_financing_disputes`, `emoney_digital_payment_disputes` → **medium/low**, 20 working days

### 2.2 Verification logic (`verification_service.py`)
- **AI-first:** `verify_with_ai()` calls Gemini (Faris persona, team SOP injected from `plugin_context.py`) → JSON `{result, checks, evidence_refs, manual_review_reason}`.
- **Fallback:** deterministic rules when no `GEMINI_API_KEY` — location discrepancy (Johor vs KL) → MANUAL_REVIEW; amount > RM 5,000 → MANUAL_REVIEW; else PASS.

## 3. MCP Layer (Model Context Protocol)

Exposed at `/api/mcp/*` (`backend/app/routes/mcp.py`) and declared in `mcp.json` as 3 HTTP servers pointing at the backend.

| MCP Server | Tool | Service call | Status |
|---|---|---|---|
| `core_banking_mcp` | `verify_banking_evidence` | `verification_service.verify_case()` | real |
| `core_banking_mcp` | `query_core_ledger` | `ledger_service.query_core_ledger()` | real (reads DB) |
| `gmail_intake_mcp` | `gmail_poll_unread` | `gmail_sync_agent.run_sync_cycle()` | real |
| `financial_resolution_mcp` | `post_journal_entry` | `resolution_service.resolve_financials()` | real |

Bonus convenience endpoint: `GET /api/mcp/gmail/poll` triggers an immediate Gmail sync.

The expert team (CodeBuddy/WorkBuddy) is designed to invoke these tools; the backend routes are the single source of truth so a demo never breaks if the agent layer is offline.

## 4. External Integrations

| Integration | Purpose | Implementation | Env vars |
|---|---|---|---|
| Gmail REST API | Poll unread complaint inbox | `gmail_sync_agent.py` — OAuth refresh-token flow, base64 decode, header/body extraction | `GMAIL_REFRESH_TOKEN`, `GMAIL_EMAIL`, `GOOGLE_CLIENT_ID/SECRET` |
| Google Cloud Pub/Sub (optional) | Push webhook on new mail | `POST /api/webhooks/gmail` + `/gmail/watch` | `GOOGLE_PUB_SUB_TOPIC` |
| Gmail SMTP / API | Send resolution emails | `communication_service.send_outbound_email()` — SMTP first, Gmail API fallback | `SMTP_USER`, `SMTP_PASSWORD` |
| Gemini (Google GenAI) | AI classification / verification / summaries / copilot / taskforce briefs | `gemini_client.py`, `copilot_service.py`, `taskforce_service.py` — all with rule-based fallback | `GEMINI_API_KEY`, `GEMINI_MODEL` |

All AI calls fail-safe: **no API key → rule-based fallback → demo never crashes.**

## 5. Data Model

- **`dispute_cases`** (`models/case.py`): `id` (DISP-2026-XXXX), customer fields, `category`, `urgency`, `status` (PENDING/PASS/FAIL/MANUAL_REVIEW/FINANCIALLY_RESOLVED), `verification_result`, `amount`, SLA timestamps (`received_at`, `due_date`), `processing_time`, encrypted PII columns, and JSON blobs: `ocr_results`, `classification`, `verification`, `financial_resolution`, `communication`, `audit_log`.
- **`audit_log`** (`models/audit.py`): separate per-case audit events (actor, action, detail).
- **`SystemSettings`** (`models/settings.py`): stores encrypted Gmail credentials + connection state.

**Storage:** SQLModel ORM over SQLite (local, WAL mode) with automatic fallback from PostgreSQL/MySQL if the remote DB is unreachable (`database.py`).

## 6. API Surface (REST)

| Router | Prefix | Key endpoints |
|---|---|---|
| `cases.py` | `/api/cases` | list (filter/search), get, patch (status/resolution + email trigger) |
| `intake.py` | `/api/intake` | `POST` — simulate complaint intake through full pipeline |
| `mcp.py` | `/api/mcp` | `/tools`, `/execute`, `/gmail/poll` |
| `taskforce.py` | `/api/taskforce` | `/overview`, `/brief/{case_id}` |
| `copilot.py` | `/api/copilot` | AI assistant query (Gemini + fallback) |
| `audit.py` | `/api/audit` | audit trail queries |
| `webhooks.py` | `/api/webhooks` | Gmail Pub/Sub push + watch registration |
| `settings.py` | `/api/settings` | Gmail connection / OAuth state |

## 7. Taskforce Layer (Frontend + Service)

`taskforce_service.py` derives from live case data: squads (Fraud Strike Cell, Billing Desk, Conduct Panel), missions, priority scores, straight-through rate, manual escalations, high-value exposure. `CopilotService` (Aegis) answers natural-language questions about the pipeline using live data + Gemini, with full rule-based fallback.

## 8. Security

- Field-level Fernet AES-256 encryption of NRIC / account number / amount at rest (`encryption_service.py`).
- Account masking on all API responses (`mask_account` → `****4321`).
- Gmail tokens stored encrypted in DB or env; never logged.
- Dynamic self-recipient protection in email dispatch.

## 9. Deployment

- **Backend:** FastAPI + uvicorn (local `127.0.0.1:8000`, prod on Render — `render.yaml`).
- **Frontend:** React (Vite), dev proxy to backend; production build served separately.
- **Env config:** `.env` → `GEMINI_API_KEY`, `DATABASE_URL`, `ENCRYPTION_KEY`, `GMAIL_*`, `GOOGLE_*`, `SMTP_*`.
- **Auto-seed:** `main.py` seeds demo cases from `mock_cases.json` when the DB is empty.

## 10. Current Known Gaps (code level)

| Gap | File(s) | Impact |
|---|---|---|
| Dashboard stat cards, AuditLog page, ManualReview still read static `mockData.js` instead of backend | `Dashboard.jsx`, `AuditLog.jsx`, `ManualReview.jsx` | Frontend stats/audit don't reflect live DB |
| Verification doesn't receive account number context | `intake_service.py:71` | Faris AI sees category/amount/text only |
| Seed cases are pre-baked, not pipeline-run | `main.py` `seed_database` | Live demo needs a fresh intake to show the flow |

> Legend: **real** = wired to actual backend logic and verified running; **fallback** = rule-based path active when no Gemini key.
