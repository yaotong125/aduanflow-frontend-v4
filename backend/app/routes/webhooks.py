import os
import json
import base64
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlmodel import Session, select
import requests

from backend.app.database import get_session, engine
from backend.app.services.gmail_sync_agent import gmail_sync_agent
from backend.app.services.encryption_service import encryption_service

logger = logging.getLogger("aduanflow")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/gmail")
async def gmail_pubsub_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Native Google Cloud Pub/Sub Push Webhook Endpoint.
    Triggered instantly whenever a new complaint email arrives in Gmail mailbox.
    """
    try:
        payload = await request.json()
        logger.info(f"[GmailWebhook] LIVE PUB/SUB WEBHOOK RECEIVED: {payload}")

        # Dispatch sync cycle asynchronously in FastAPI background tasks to prevent event loop blocking
        background_tasks.add_task(gmail_sync_agent.run_sync_cycle)

        return {
            "status": "success",
            "message": "Webhook processed, sync cycle dispatched in background",
            "receivedAt": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        logger.error(f"[GmailWebhook] Error parsing webhook: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/gmail/watch")
def trigger_gmail_watch(topic_name: Optional[str] = None, session: Session = Depends(get_session)):
    """
    Programmatically register Gmail API users.watch() webhook subscription.
    Connects Gmail mailbox notifications to Google Cloud Pub/Sub topic.
    """
    raw_topic = topic_name or os.getenv("GOOGLE_PUB_SUB_TOPIC")
    if not raw_topic:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_PUB_SUB_TOPIC missing. Example: projects/YOUR_PROJECT_ID/topics/gmail-incoming-emails"
        )

    creds = gmail_sync_agent.get_decrypted_credentials(session)
    raw_refresh = creds.get("refresh_token") if creds.get("connected") else None
    if not raw_refresh:
        raw_refresh = os.getenv("GMAIL_REFRESH_TOKEN")
    if not raw_refresh:
        raise HTTPException(
            status_code=400,
            detail="No Gmail refresh token available. Connect Gmail first via Settings > Gmail & Integrations."
        )
    client_id = os.getenv("GOOGLE_CLIENT_ID") or "1041907708486-uvplue4dp8pl64bre8a36u0qs5vc8lsn.apps.googleusercontent.com"
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or "GOCSPX-AduanFlowAutoSecretKey2026"

    # Fetch Access Token
    token_res = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": raw_refresh,
        "grant_type": "refresh_token"
    }, timeout=10)

    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {token_res.text}")

    access_token = token_res.json().get("access_token")

    # Execute users.watch() request
    watch_url = "https://gmail.googleapis.com/gmail/v1/users/me/watch"
    watch_body = {
        "topicName": raw_topic,
        "labelIds": ["INBOX"]
    }

    watch_res = requests.post(
        watch_url,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=watch_body,
        timeout=10
    )

    if watch_res.status_code != 200:
        logger.error(f"[GmailWatch] watch() failed: {watch_res.status_code} - {watch_res.text}")
        raise HTTPException(status_code=watch_res.status_code, detail=watch_res.text)

    watch_data = watch_res.json()
    logger.info(f"[GmailWatch] SUCCESS! Gmail watch active: {watch_data}")

    return {
        "status": "active",
        "topicName": raw_topic,
        "historyId": watch_data.get("historyId"),
        "expiration": watch_data.get("expiration"),
        "message": "Native Gmail API Watch webhook active!"
    }
