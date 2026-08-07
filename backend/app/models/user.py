from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON, Column

class User(SQLModel, table=True):
    """
    User model for multi-investigator & compliance officer access control.
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: str
    role: str = Field(default="investigator")  # investigator, admin
    department: str = Field(default="Dispute Resolution Taskforce")
    is_active: bool = Field(default=True)
    
    hashed_password: str = Field(default="")
    
    # Alert Preferences
    email_enabled: bool = Field(default=True)
    quiet_hours: bool = Field(default=False)

    # Notification Toggles
    notif_case_assigned: bool = Field(default=True)
    notif_status_changed: bool = Field(default=True)
    notif_sla_breach: bool = Field(default=True)
    notif_manual_review: bool = Field(default=False)
    notif_weekly_digest: bool = Field(default=True)

    # Security & Checklist Toggles
    sec_2fa: bool = Field(default=False)
    sec_password_expiry: bool = Field(default=False)
    sec_ip_allowlist: bool = Field(default=False)
    sec_new_device_alert: bool = Field(default=True)
    sec_session_timeout: str = Field(default="30")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
