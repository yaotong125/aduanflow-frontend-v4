from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class AuditLogBase(SQLModel):
    case_id: str = Field(index=True)
    actor: str = Field(index=True)  # Email MCP, Intake Agent, Security Agent, Classification Agent, Verification Agent, Financial Agent, Comms Agent, Gmail Sync Agent
    action: str
    detail: Optional[str] = None


class AuditLog(AuditLogBase, table=True):
    __tablename__ = "audit_logs"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLogCreate(AuditLogBase):
    """Schema for manually creating an audit log entry via POST /audit."""
    id: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogRead(AuditLogBase):
    id: str
    created_at: datetime
