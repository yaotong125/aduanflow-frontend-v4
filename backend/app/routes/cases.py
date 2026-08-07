from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from backend.app.database import get_session
from backend.app.models.case import Case, CaseUpdate

router = APIRouter(prefix="/cases", tags=["cases"])

def format_case(c: Case) -> dict:
    return {
        "id": c.id,
        "customerName": c.customer_name,
        "customerEmail": c.customer_email,
        "maskedAccount": c.masked_account,
        "category": c.category,
        "urgency": c.urgency,
        "status": c.status,
        "verificationResult": c.verification_result or c.status,
        "amount": c.amount,
        "assignedTo": c.assigned_to,
        "receivedAt": c.received_at.isoformat() if hasattr(c.received_at, 'isoformat') else str(c.received_at),
        "dueDate": c.due_date.isoformat() if (c.due_date and hasattr(c.due_date, 'isoformat')) else None,

        "processingTime": c.processing_time or "—",
        "emailSubject": c.email_subject,
        "emailBody": c.email_body,
        "ocrResults": c.ocr_results,
        "classification": c.classification,
        "verification": c.verification,
        "financialResolution": c.financial_resolution,
        "communication": c.communication,
        "auditLog": c.audit_log or [],
    }

@router.get("")
def list_cases(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List dispute cases with filtering and search."""
    statement = select(Case)
    if status:
        statement = statement.where(Case.status == status)
    if category:
        statement = statement.where(Case.category == category)
    
    results = session.exec(statement).all()
    
    if search:
        s = search.lower()
        results = [
            c for c in results 
            if s in c.id.lower() or s in c.customer_name.lower() or s in c.customer_email.lower()
        ]
        
    return [format_case(c) for c in results]

@router.get("/{case_id}")
def get_case(case_id: str, session: Session = Depends(get_session)):
    """Get a single dispute case details."""
    case_item = session.get(Case, case_id)
    if not case_item:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return format_case(case_item)

@router.patch("/{case_id}")
def update_case(case_id: str, case_update: CaseUpdate, session: Session = Depends(get_session)):
    """Update case status, assignment, or resolution."""
    db_case = session.get(Case, case_id)
    if not db_case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
    case_data = case_update.model_dump(exclude_unset=True)
    for key, value in case_data.items():
        setattr(db_case, key, value)
        
    session.add(db_case)
    session.commit()
    session.refresh(db_case)

    # If investigator approves / resolves case, dispatch resolution email to customer
    if case_update.status and case_update.status in ['PASS']:
        try:
            from backend.app.services.communication_service import communication_service
            subject = f"Resolution Notice: Dispute Case {db_case.id} Resolved"
            body = (
                f"Dear {db_case.customer_name},\n\n"
                f"Your dispute case {db_case.id} regarding {db_case.category} of RM {db_case.amount} "
                f"has been reviewed and approved by our dispute team. A credit adjustment has been posted to your account.\n\n"
                f"Mandatory BNM & FMOS Disclosures:\n"
                f"1. BNM Policy Document on Complaints Handling: Processed within SLA mandate.\n"
                f"2. FMOS Redress Notice: Should you remain dissatisfied, you may refer your case to FMOS within 6 months.\n\n"
                f"Regards,\nAduanFlow Dispute Automation Team"
            )
            communication_service.send_outbound_email(
                to_email=db_case.customer_email,
                subject=subject,
                body=body
            )
        except Exception:
            pass

    return format_case(db_case)
