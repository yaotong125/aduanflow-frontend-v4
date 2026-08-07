from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, JSON, Column
import uuid

class CaseBase(SQLModel):
    id: str = Field(primary_key=True) # e.g. DISP-2026-00124
    customer_name: str = Field(index=True)
    customer_email: str
    masked_account: str
    masked_card: Optional[str] = Field(default=None)
    category: str = Field(index=True)
    urgency: str = Field(default="medium")
    status: str = Field(default="MANUAL_REVIEW", index=True) # PASS, FAIL, MANUAL_REVIEW
    verification_result: Optional[str] = Field(default=None)
    amount: float = Field(default=0.0)
    assigned_to: Optional[str] = Field(default=None)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = Field(default=None)
    processing_time: Optional[str] = Field(default="—")
    email_subject: Optional[str] = Field(default=None)
    email_body: Optional[str] = Field(default=None)
    
    # Encrypted fields stored at rest
    nric_encrypted: Optional[str] = Field(default=None)
    account_number_encrypted: Optional[str] = Field(default=None)
    card_number_encrypted: Optional[str] = Field(default=None)
    dispute_amount_encrypted: Optional[str] = Field(default=None)

    # JSON structures for deep case details
    ocr_results: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    classification: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    verification: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    financial_resolution: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    communication: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    audit_log: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

class Case(CaseBase, table=True):
    __tablename__ = "dispute_cases"

class CaseCreate(CaseBase):
    pass

class CaseRead(CaseBase):
    pass

class CaseUpdate(SQLModel):
    status: Optional[str] = None
    verification_result: Optional[str] = None
    assigned_to: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[str] = None
    financial_resolution: Optional[Dict[str, Any]] = None
    communication: Optional[Dict[str, Any]] = None
    audit_log: Optional[List[Dict[str, Any]]] = None
