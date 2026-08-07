from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import uuid

from backend.app.database import get_session
from backend.app.models.audit import AuditLog, AuditLogCreate, AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=List[AuditLogRead])
def list_audit_logs(
    actor: Optional[str] = None,
    case_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    """Fetch system audit trail with optional actor/case filters and pagination."""
    statement = select(AuditLog).order_by(AuditLog.created_at.desc())
    if actor:
        statement = statement.where(AuditLog.actor == actor)
    if case_id:
        statement = statement.where(AuditLog.case_id == case_id)
    statement = statement.offset(offset).limit(limit)
    return session.exec(statement).all()


@router.post("", response_model=AuditLogRead, status_code=201)
def create_audit_log(
    payload: AuditLogCreate,
    session: Session = Depends(get_session),
):
    """Manually create an audit log entry (for investigator annotations or admin tooling)."""
    row = AuditLog(
        id=payload.id or str(uuid.uuid4()),
        case_id=payload.case_id,
        actor=payload.actor,
        action=payload.action,
        detail=payload.detail,
        created_at=payload.created_at or datetime.utcnow(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{log_id}", status_code=204)
def delete_audit_log(
    log_id: str,
    session: Session = Depends(get_session),
):
    """Delete a specific audit log entry by ID (admin/cleanup operation)."""
    row = session.get(AuditLog, log_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Audit log entry {log_id} not found")
    session.delete(row)
    session.commit()
    return None


@router.get("/stats", tags=["audit"])
def audit_stats(session: Session = Depends(get_session)):
    """
    Return a summary of audit log activity:
    - Total event count
    - Breakdown by actor
    - Most recently active cases
    """
    all_logs = session.exec(select(AuditLog).order_by(AuditLog.created_at.desc())).all()

    actor_counts: dict = {}
    case_ids_seen: List[str] = []
    for log in all_logs:
        actor_counts[log.actor] = actor_counts.get(log.actor, 0) + 1
        if log.case_id not in case_ids_seen:
            case_ids_seen.append(log.case_id)

    return {
        "total_events": len(all_logs),
        "actor_breakdown": actor_counts,
        "recent_cases": case_ids_seen[:10],
        "last_event_at": all_logs[0].created_at.isoformat() if all_logs else None,
    }
