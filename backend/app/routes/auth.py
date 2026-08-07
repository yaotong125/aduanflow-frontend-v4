import hashlib
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select, or_
from backend.app.database import get_session
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

def hash_password(password: str) -> str:
    """SHA256 hash for password storage."""
    return hashlib.sha256(password.encode()).hexdigest()

def _find_user_by_username(session: Session, username: str) -> Optional[User]:
    """
    Find a user by username (short name) or full email.
    Supports both 'admin' and 'admin@aduanflow.com' style lookups.
    """
    return session.exec(
        select(User).where(
            or_(
                User.email == username,
                User.email == f"{username}@aduanflow.com",
                User.full_name == username,
            )
        )
    ).first()

@router.post("/login")
def login(credentials: Dict[str, str], session: Session = Depends(get_session)):
    username = credentials.get("username", "").strip()
    password = credentials.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    try:
        user = _find_user_by_username(session, username)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}\n{traceback.format_exc()}")
    
    # Auto-seed demo users if DB is empty — ensures demo always works
    if not user:
        if username in ("admin", "admin@aduanflow.com"):
            user = User(
                email="admin@aduanflow.com",
                full_name="Admin",
                role="admin",
                hashed_password=hash_password("admin123")
            )
        elif username in ("investigator", "investigator@aduanflow.com"):
            user = User(
                email="investigator@aduanflow.com",
                full_name="Investigator",
                role="investigator",
                hashed_password=hash_password("investor123")
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        try:
            session.add(user)
            session.commit()
            session.refresh(user)
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Database seed failed: {str(e)}")

    if user.hashed_password != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Derive short username from email for frontend display
    short_username = user.email.split("@")[0] if "@" in user.email else user.email

    return {
        "id": user.id,
        "username": short_username,
        "name": user.full_name,
        "role": user.role,
        "email": user.email,
    }

@router.post("/change-password")
def change_password(data: Dict[str, str], session: Session = Depends(get_session)):
    username = data.get("username", "").strip()
    current_pwd = data.get("current_password", "")
    new_pwd = data.get("new_password", "")

    if not username or not current_pwd or not new_pwd:
        raise HTTPException(status_code=400, detail="All password fields are required")

    user = _find_user_by_username(session, username)
    if not user or user.hashed_password != hash_password(current_pwd):
        raise HTTPException(status_code=401, detail="Invalid current password")

    if len(new_pwd) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    user.hashed_password = hash_password(new_pwd)
    session.add(user)
    session.commit()
    return {"status": "success", "message": "Password updated successfully"}

@router.get("/settings/{username}")
def get_settings(username: str, session: Session = Depends(get_session)):
    user = _find_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "displayName": user.full_name,
        "emailEnabled": user.email_enabled,
        "quietHours": user.quiet_hours,
        "checklistState": {
            "2fa": user.sec_2fa,
            "password_expiry": user.sec_password_expiry,
            "ip_allowlist": user.sec_ip_allowlist
        },
        "notifs": {
            "case_assigned": user.notif_case_assigned,
            "status_changed": user.notif_status_changed,
            "sla_breach": user.notif_sla_breach,
            "manual_review": user.notif_manual_review,
            "weekly_digest": user.notif_weekly_digest
        },
        "security": {
            "new_device_alert": user.sec_new_device_alert,
            "session_timeout": user.sec_session_timeout
        }
    }

@router.post("/settings/{username}")
def update_settings(username: str, settings: Dict[str, Any], session: Session = Depends(get_session)):
    user = _find_user_by_username(session, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if "displayName" in settings:
        user.full_name = settings["displayName"]
    
    if "emailEnabled" in settings:
        user.email_enabled = settings["emailEnabled"]
    if "quietHours" in settings:
        user.quiet_hours = settings["quietHours"]

    checklist = settings.get("checklistState", {})
    if "2fa" in checklist:
        user.sec_2fa = checklist["2fa"]
    if "password_expiry" in checklist:
        user.sec_password_expiry = checklist["password_expiry"]
    if "ip_allowlist" in checklist:
        user.sec_ip_allowlist = checklist["ip_allowlist"]

    notifs = settings.get("notifs", {})
    if "case_assigned" in notifs:
        user.notif_case_assigned = notifs["case_assigned"]
    if "status_changed" in notifs:
        user.notif_status_changed = notifs["status_changed"]
    if "sla_breach" in notifs:
        user.notif_sla_breach = notifs["sla_breach"]
    if "manual_review" in notifs:
        user.notif_manual_review = notifs["manual_review"]
    if "weekly_digest" in notifs:
        user.notif_weekly_digest = notifs["weekly_digest"]

    security = settings.get("security", {})
    if "new_device_alert" in security:
        user.sec_new_device_alert = security["new_device_alert"]
    if "session_timeout" in security:
        user.sec_session_timeout = security["session_timeout"]
    
    session.add(user)
    session.commit()
    return {"status": "success"}
