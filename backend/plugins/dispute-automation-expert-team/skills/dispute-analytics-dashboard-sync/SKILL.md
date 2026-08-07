---
name: dispute-analytics-dashboard-sync
description: "Real-time dispute operations sync for statuses, SLA alerts, throughput, latency, and investigator workload metrics."
---

# Dispute analytics dashboard sync

Use when a dispute changes state or when the operations dashboard needs refreshed metrics and SLA alerts.

## Workflow

1. Read the latest case status and timestamps.
2. Push or prepare a dashboard payload containing:
   - `case_status` from RECEIVED, ACKNOWLEDGED, VERIFYING, FINANCIALLY_RESOLVED, ESCALATED_MANUAL, CLOSED
   - `sla_countdown`
   - `processing_latency`
   - `classification_accuracy` when available
   - `financial_volume_processed`
   - `investigator_workload`
3. Trigger an alert when a case is within 48 hours of a BNM breach threshold.
4. Recompute roll-up KPIs:
   - average turnaround time
   - automated PASS-case completion time target under 5 minutes
   - pipeline throughput
   - queue distribution
5. Return a sync summary with:
   - `dashboard_payload`
   - `alerts_triggered`
   - `kpi_snapshot`
   - `retry_actions` if sync failed

## Output rules

- Keep dashboard status aligned with the latest verified case state.
- Separate real-time case payloads from aggregate KPI snapshots.
- If the dashboard endpoint is unavailable, return a valid payload ready for later sync.
