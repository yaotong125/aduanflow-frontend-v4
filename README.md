# AduanFlow AI — Autonomous Banking Dispute Resolution System

> **AI-powered, fully automated banking complaint handling**  for the Tencent Cloud × UTM Hackathon 2026 (AI Agent Track).

AduanFlow is an **agentic AI pipeline** that automatically ingests customer complaints from email, extracts evidence (even from scanned PDFs via OCR), classifies claims under Bank Negara Malaysia (BNM) rules, verifies against banking data, resolves eligible disputes, and responds with BNM/FMOS-compliant emails — all without human touch for high-confidence cases.

--- 

## ✨ Features

- **📥 Autonomous Gmail sync agent** — polls the complaints mailbox every 30s, ingests new unread complaints automatically.
- **🤖 Agentic AI intake** — the *Rhea* agent decides whether to call the PDF-OCR tool and extracts entities (account, card, NRIC, amount) using Gemini tool-calling.
- **🧾 Multi-layer OCR** — text-layer *PyMuPDF* + **RapidOCR** (pure Python/ONNX) + *Tesseract* fallback for scanned PDFs.
- **🏛️ BNM/FMOS compliance** — dispute classification mapped to mandated SLA working days, with governance stamps and auditable decision trails.
- **✅ Three-state verdict engine** — PASS (fully automated resolution), MANUAL_REVIEW (human escalation), FAIL (claim not upheld) driven by a verification agent.
- **🔐 PII-at-rest encryption** — NRIC, account, card, and dispute amount encrypted with Fernet (AES-256) before storage.
- **📊 Modern React dashboard** — real-time case list, statuses, agent pipeline trace, and customer communication records.
- **☁️ Cloud-ready storage** — Supabase PostgreSQL, with automatic SQLite fallback for offline/dev.

---

## System Architecture

```
Customer Email
      │
      ▼
[Gmail Sync Agent]  ──►  (IMAP / Gmail API, poll 30s)
      │
      ▼
[Rhea — Intake Agent]  ──►  tool: pdf_extract (PyMuPDF + RapidOCR)
      │                      extracts account / card / amount / NRIC
      ▼
[Nadia — Classification]  ──►  BNM SLA category + urgency
      │
      ▼
[Faris — Verification/MCP]  ──►  PASS / MANUAL_REVIEW / FAIL
      │
      ▼
[Resolution + Communication] ──►  compliant customer email (SMTP/Gmail)
      │
      ▼
[Supabase PostgreSQL]  ◄──►  [React Dashboard]
```

**Multi-Agent cast** (inspired by the taskforce team playbook):

| Agent | Role |
|-------|------|
| **Rhea** | Intake & entity extraction, decides when to call OCR tool |
| **Nadia** | Dispute classifier & BNM compliance strategist |
| **Faris** | MCP verification & resolution analyst |
| **Sync Agent** | Autonomous Gmail mailbox poller |

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn, SQLModel, SQLAlchemy |
| AI | Google Gemini (via `google-genai`), native tool-calling |
| OCR | PyMuPDF, RapidOCR (ONNX), pytesseract (+ Tesseract engine) |
| Storage | Supabase PostgreSQL, SQLite fallback |
| Encryption | Fernet (cryptography, AES-256) |
| Email | Gmail IMAP + SMTP |
| Frontend | React 18, Vite, Tailwind CSS |
| Deploy | Render (free-tier) |

---

## 📦 Project Structure

```
aduanflow/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint, router wiring, seed
│   │   ├── config.py               # Env-driven settings (loads .env at import)
│   │   ├── database.py             # Engine + Supabase/SQLite (+ IPv4 pooler fallback)
│   │   ├── models/
│   │   │   ├── case.py             # Case (SQLModel ORM)
│   │   │   ├── audit.py            # AuditLog (SQLite/Audit)
│   │   │   └── settings.py         # SystemSettings (Gmail/OAuth token store)
│   │   ├── routes/                 # API routers (cases, audit, copilot, intake, taskforce, webhooks, mcp)
│   │   └── services/
│   │       ├── gmail_sync_agent.py # Autonomous IMAP/Gmail poller
│   │       ├── intake_agent.py     # Rhea: tool-calling entity extraction
│   │       ├── intake_service.py   # 5-stage intake orchestration
│   │       ├── classification_service.py  # Nadia: categorize + BNM SLA
│   │       ├── verification_service.py    # Faris: PASS/FAIL/MANUAL_REVIEW
│   │       ├── resolution_service.py      # financial posting
│   │       ├── communication_service.py   # compliant email generation/dispatch
│   │       ├── pdf_extractor.py    # OCR (RapidOCR/Tesseract)
│   │       ├── gemini_client.py    # Gemini wrapper + tool-calling
│   │       └── encryption_service.py      # Fernet PII-at-rest
│   ├── requirements.txt
│   └── mock_cases.json             # Seed data
├── frontend/
│   ├── src/                        # React app (Vite + Tailwind)
│   │   └── config.js               # API base URL (local vs Render)
│   └── package.json
├── render.yaml                     # Render declarative deploy (backend + frontend)
└── .env.example                    # (see below) environment template
```

---

## 🔧 Getting Started (Local Dev)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com)
- (Optional) Gmail app password for live complaint sync

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` in the project root (or `backend/.env`):

```env
# AI
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash

# Gmail (optional, for live sync / outbound)
GMAIL_EMAIL=aduanflow@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# Database
DATABASE_URL=postgresql://user:pass@host:5432/postgres   # optional; falls back to SQLite

# Encryption
ENCRYPTION_KEY=your_fernet_key
```

Run the API:

```bash
export PYTHONPATH=.              # Windows (PowerShell): $env:PYTHONPATH=...
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

The frontend auto-detects `localhost` and calls `http://127.0.0.1:8000`.

---

## ☁️ Deploying to Render

This repo includes a `render.yaml` Blueprint that provisions both services on Render.

1. Push this repo to GitHub.
2. In Render → **Blueprints** → **New Blueprint**, select the repo.
3. Provide the env values flagged `sync: false`:
   - `DATABASE_URL` — Supabase PostgreSQL connection string
   - `GEMINI_API_KEY`
   - `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (OAuth only)
   - `ENCRYPTION_KEY` is auto-generated; update `frontend/src/config.js` to your backend URL.

> **Note:** Render's *free tier* may block outbound **SMTP :587**. Inbound Gmail/IMAP, outbound HTTPS (:443), Postgres, and the Gmail REST API all work. For real-time outbound email on the free tier, use the **Gmail API** (`messages.send`, over HTTPS) or a third-party email API (SendGrid/Mailgun).

---

## 🤖 Demo Scenarios

Ready-to-send complaint templates to exercise the full pipeline:

| Scenario | What you send | Expected verdict |
|----------|---------------|------------------|
| **PASS** | Unauthorized card charge with legit details | `PASS` — auto-resolved & (if SMTP works) email sent |
| **FAIL** | Customer admits it was their own/authorized+OTP transaction | `FAIL` — claim not upheld |
| **MANUAL_REVIEW** | High-value dispute (> RM5k) or location inconsistency (login KL vs ATM JB) | `MANUAL_REVIEW` — escalates to human |

Example PASS body:

```
Subject: Unauthorized transaction RM1,280 on my account
Body: I did not authorize this charge. Account: 114002938471, Card: 4231-..., Amount: RM1,280
```

---

## 🌊 BNM / Compliance Highlights

- Complaints mapped to BNM **mandatory SLA timelines** (e.g. Unauthorized Transactions = 5 working days).
- **FMOS** (Financial Mediation & Ombudsman Service) escalation notice embedded in every customer email.
- Full **audit log** per case: intake → OCR → classify → verify → resolve → respond.
- Governance field: `bnm_compliant: true`, `governance_status: STAMPED_PASS`.

---

## 📌 Roadmap / Notes

- [ ] Enable Gmail API (OAuth2) for HTTPS-based outbound mail on free tier.
- [ ] Add SendGrid fallback provider.
- [ ] Expand OCR to more document layouts.
- [ ] Add customer-facing status portal.

---

> Built with ❤️ for **Tencent Cloud × UTM Hackathon 2026 — AI Agent Track**.
> Team **AduanFlow** – Banking Dispute Automation.
#   a d u a n f l o w - f r o n t e n d - v 5  
 