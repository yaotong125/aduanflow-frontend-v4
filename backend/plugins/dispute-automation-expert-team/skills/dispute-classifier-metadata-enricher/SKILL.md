---
name: dispute-classifier-metadata-enricher
description: "Banking dispute classification, entity extraction, and urgency routing across seven standard complaint categories."
---

# Dispute classifier and metadata enricher

Use for incoming banking complaints that need a normalized category, extracted entities, urgency, and routing metadata.

## Categories

1. Unauthorized transactions
2. Billing errors
3. Mis-selling claims
4. ATM or debit card disputes
5. Insurance or takaful claims
6. Loan or financing disputes
7. E-money or digital payment disputes

## Workflow

1. Read complaint text plus any OCR-extracted attachment text.
2. Extract structured entities when present:
   - NRIC or passport number
   - Core account number
   - Credit or debit card number
   - Transaction timestamp
   - Disputed amount in MYR
   - Merchant name
   - Channel
3. Map the complaint to the best-fit category and explain the confidence.
4. Score complexity and urgency:
   - HIGH / Simple / 5 working days: single unauthorized card charge, ATM cash non-dispense, billing error <= RM 5,000
   - MEDIUM / Complex / 20 working days: mis-selling, fraud-network indicators, loan interest miscalculation, e-wallet breach > RM 5,000
5. Recommend the next route: automated verification, manual review, or missing-information hold.
6. Output JSON with:
   - `category`
   - `confidence`
   - `entities`
   - `urgency_rating`
   - `complexity`
   - `sla_type`
   - `recommended_route`
   - `reasoning_summary`

## Output rules

- Preserve OCR uncertainty as confidence notes.
- If multiple categories are plausible, pick one primary category and list alternates.
- Do not fabricate identifiers or monetary amounts.
