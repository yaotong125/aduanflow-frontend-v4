from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional
from backend.app.database import get_session
from backend.app.services.intake_service import intake_service
from backend.app.models.case import CaseRead

router = APIRouter(prefix="/intake", tags=["intake"])

class IntakeRequest(BaseModel):
    customer_name: str
    customer_email: str
    account_number: str
    nric: str
    amount: float
    email_subject: str
    email_body: str
    attachment_name: Optional[str] = None
    card_number: Optional[str] = None

@router.post("", response_model=CaseRead)
def submit_complaint(payload: IntakeRequest, session: Session = Depends(get_session)):
    """Simulate receiving an email/attachment intake for processing through the AI dispute pipeline."""
    case_obj = intake_service.process_incoming_complaint(
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        account_number=payload.account_number,
        nric=payload.nric,
        amount=payload.amount,
        email_subject=payload.email_subject,
        email_body=payload.email_body,
        attachment_name=payload.attachment_name,
        card_number=payload.card_number,
    )
    
    session.add(case_obj)
    session.commit()
    session.refresh(case_obj)
    return case_obj

