---
name: core-system-mcp-verifier
description: "Core banking evidence verification through ledger, switch, ATM, fraud, and CRM data sources exposed through MCP or equivalent interfaces."
---

# Core system MCP verifier

Use when a classified dispute needs factual verification against internal banking systems before any financial decision is made.

## Workflow

1. Build a verification checklist from the case payload:
   - transaction reference
   - account or card identifier
   - amount
   - channel
   - dispute window
2. Query the available data sources through MCP or equivalent interfaces:
   - Core ledger
   - Switch logs
   - ATM journals
   - Fraud and device logs
   - OTP or 2FA records
   - CRM notes
3. Evaluate evidence and return one decision:
   - `PASS`: confirmed system error, duplicate charge, host timeout, ATM cash issue, or valid refund authorization
   - `FAIL`: authenticated transaction with no system anomaly and evidence refuting the claim
   - `MANUAL_REVIEW`: value > RM 50,000, mis-selling review, conflicting fraud signals, or missing logs
4. Produce a verification bundle with:
   - `decision`
   - `evidence_summary`
   - `systems_checked`
   - `missing_evidence`
   - `decision_rationale`
   - `recommended_next_step`

## Output rules

- If a required system cannot be queried, say so and bias toward `MANUAL_REVIEW`.
- Keep evidence summaries auditable and source-specific.
- Never turn missing evidence into a confident PASS or FAIL decision.
