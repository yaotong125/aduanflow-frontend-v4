---
name: bnm-fmos-compliance-governor
description: "BNM and FMOS dispute-handling policy enforcement for SLA calculation, disclosure rules, and regulatory stamps."
---

# BNM and FMOS compliance governor

Use for banking complaint cases that need turnaround-time calculation, disclosure checks, or a structured regulatory stamp.

## Workflow

1. Read the case facts, complaint received date, complexity rating, current status, and any third-party dependency.
2. Set the acknowledgment deadline to 1 working day from intake.
3. Set the resolution deadline:
   - Simple case: 5 working days
   - Complex case: 20 working days
   - Third-party exception: allow extension up to 30 working days and require audit logging
4. If a complex case crosses each 10-working-day interval, require a progress update notice.
5. Determine FMOS eligibility:
   - Monetary claim <= RM 250,000
   - Status is REJECTED, PARTIAL_SETTLEMENT, or customer remains dissatisfied
6. Append the mandatory FMOS disclosure when eligible:
   - "If you are dissatisfied with our final decision, you have the right to refer this matter to the Financial Markets Ombudsman Service (FMOS) within 6 months of this notice."
7. Output a `BNM_Compliance_Stamp` object with:
   - `ack_due_date`
   - `target_completion_date`
   - `days_remaining`
   - `fmos_eligible`
   - `mandatory_disclosures`
   - `progress_update_schedule`
   - `audit_notes`

## Output rules

- Use working-day logic, not calendar-day logic.
- If the intake date or complexity is missing, ask for it or state the assumption explicitly.
- Never suppress mandatory disclosures once the trigger conditions are met.
