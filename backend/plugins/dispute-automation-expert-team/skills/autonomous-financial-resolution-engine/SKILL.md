---
name: autonomous-financial-resolution-engine
description: "Automated refund, fee reversal, journal generation, and status updates for PASS-verified banking dispute cases."
---

# Autonomous financial resolution engine

Use after verification returns `PASS` and the dispute qualifies for automated financial settlement.

## Workflow

1. Read the approved case amount, affected fees, interest impact, account destination, and settlement reference.
2. Calculate the financial adjustment package:
   - principal refund
   - dispute fee reversal
   - accrued or late-fee adjustment
3. Generate balanced double-entry journals, for example:
   - Debit: Bank Sundry Loss or Dispute Suspension Account
   - Credit: Customer Savings, Current, or E-Money Account
4. Post the settlement through the core financial interface or prepare the posting payload if execution access is unavailable.
5. Stamp audit fields:
   - `transaction_reference_id`
   - `batch_reference`
   - `execution_timestamp`
   - `executed_by`
6. Return a settlement record with status `FINANCIALLY_RESOLVED`.

## Output rules

- The journal must balance exactly.
- If any required amount is missing, stop and request clarification.
- Keep a full audit trail for every automated adjustment.
- If posting access is unavailable, output the exact posting payload and mark it pending execution.
