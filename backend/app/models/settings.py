from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class SystemSettingsBase(SQLModel):
    id: str = Field(default="global_settings", primary_key=True)
    gmail_email: Optional[str] = Field(default=None)
    gmail_refresh_token_encrypted: Optional[str] = Field(default=None)
    is_gmail_connected: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SystemSettings(SystemSettingsBase, table=True):
    __tablename__ = "system_settings"

class GmailTokenPayload(SQLModel):
    email: str
    refresh_token: str
    app_password: Optional[str] = None

class GmailStatusResponse(SQLModel):
    is_connected: bool
    email: Optional[str] = None
    updated_at: Optional[datetime] = None
