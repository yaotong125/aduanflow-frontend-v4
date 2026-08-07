import os
import logging
from datetime import datetime
from sqlmodel import Session, select
from backend.app.database import engine
from backend.app.models.settings import SystemSettings
from backend.app.models.audit import AuditLog
from backend.app.services.encryption_service import encryption_service
from backend.app.services.intake_service import intake_service
from backend.app.services.classification_service import classification_service

logger = logging.getLogger("aduanflow")

class GmailSyncAgent:
    """
    Independent AI Worker Agent dedicated solely to Gmail Complaints Mailbox Synchronization.
    
    Responsibilities:
    1. Retrieve encrypted OAuth refresh token from Database (SystemSettings).
    2. Decrypt token safely in memory using Fernet AES-256.
    3. Connect to Google Gmail API & poll unread complaint emails.
    4. Pass extracted complaint data into the dispute resolution engine without modifying Expert Team logic.
    """

    def __init__(self):
        self.agent_name = "Gmail Sync Agent"
        self.role = "Automated Mailbox Synchronizer & OAuth Connector"

    def get_decrypted_credentials(self, session: Session) -> dict:
        """Fetch and decrypt stored Gmail credentials from Database or Environment Variables."""
        env_token = os.getenv("GMAIL_REFRESH_TOKEN")
        env_email = os.getenv("GMAIL_EMAIL") or "yaodongfscorporateservices@gmail.com"
        env_app_password = os.getenv("GMAIL_APP_PASSWORD")

        # Prefer IMAP app-password path when provided (simplest for SMTP/IMAP access)
        if env_app_password:
            return {
                "connected": True,
                "email": env_email,
                "app_password": env_app_password.replace(" ", ""),
                "method": "imap",
            }

        if env_token:
            return {
                "connected": True,
                "email": env_email,
                "refresh_token": env_token,
                "client_id": os.getenv("GOOGLE_CLIENT_ID") or "1041907708486-uvplue4dp8pl64bre8a36u0qs5vc8lsn.apps.googleusercontent.com",
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET") or "GOCSPX-AduanFlowAutoSecretKey2026",
                "method": "oauth",
            }

        settings_obj = session.get(SystemSettings, "global_settings")
        if not settings_obj or not settings_obj.is_gmail_connected:
            return {"connected": False, "reason": "No Gmail account connected in Database settings."}

        try:
            raw_token = encryption_service.decrypt(settings_obj.gmail_refresh_token_encrypted)
            return {
                "connected": True,
                "email": settings_obj.gmail_email,
                "refresh_token": raw_token,
            }
        except Exception as e:
            logger.error(f"[{self.agent_name}] Decryption failed: {e}")
            return {"connected": False, "reason": f"Token decryption error: {str(e)}"}

    def run_sync_cycle(self) -> dict:
        """
        Execute an independent sync cycle:
        1. Fetch credentials from DB
        2. Authenticate & fetch new unread complaint emails via Google Gmail REST API (q=is:unread)
        3. Extract metadata, mark as read, and pass through the 5-stage AI dispute resolution pipeline.
        """
        import os
        import re
        import base64
        import requests
        import traceback

        try:
            with Session(engine) as session:
                creds = self.get_decrypted_credentials(session)
                if not creds.get("connected"):
                    logger.warning(f"[{self.agent_name}] Cannot run sync: {creds.get('reason')}")
                    return {"status": "inactive", "message": creds.get("reason")}

                target_email = creds["email"]

                # IMAP path (app password) — simpler than OAuth and works with SMTP app passwords
                if creds.get("method") == "imap":
                    return self.run_sync_cycle_imap(creds)

                raw_refresh = creds.get("refresh_token")
                raw_client_id = os.getenv("GOOGLE_CLIENT_ID") or "1041907708486-uvplue4dp8pl64bre8a36u0qs5vc8lsn.apps.googleusercontent.com"
                raw_client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or "GOCSPX-AduanFlowAutoSecretKey2026"

                logger.info(f"[{self.agent_name}] Active! Synchronizing inbox for {target_email} using Google OAuth 2.0...")

                # 1. Fetch fresh access token
                access_token = None
                if raw_refresh:
                    try:
                        token_res = requests.post("https://oauth2.googleapis.com/token", data={
                            "client_id": raw_client_id,
                            "client_secret": raw_client_secret,
                            "refresh_token": raw_refresh,
                            "grant_type": "refresh_token"
                        }, timeout=10)
                        if token_res.status_code == 200:
                            access_token = token_res.json().get("access_token")
                    except Exception as t_err:
                        logger.error(f"[{self.agent_name}] Token refresh error: {t_err}")

                if not access_token:
                    logger.warning(f"[{self.agent_name}] Could not obtain access token. Inbox sync paused.")
                    return {"status": "inactive", "message": "Could not obtain access token for Gmail API."}

                # 2. Fetch unread complaint messages query (clean params dictionary)
                headers = {"Authorization": f"Bearer {access_token}"}
                list_res = requests.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers=headers,
                    params={"q": 'is:unread -from:me -subject:"Resolution Notice" -subject:"Delivery Status"'},
                    timeout=10
                )

                if list_res.status_code != 200:
                    logger.warning(f"[{self.agent_name}] Gmail API list returned status {list_res.status_code}: {list_res.text}")
                    return {"status": "error", "message": f"Gmail API error: {list_res.status_code}"}

                messages_data = list_res.json().get("messages", [])

                if not messages_data:
                    logger.info(f"[{self.agent_name}] No unread complaint emails found in {target_email}.")
                    return {"status": "success", "mailbox": target_email, "synced_cases": [], "message": "Inbox clear. No unread complaints."}

                messages_data = messages_data[:5]
                synced_cases = []
                for msg_item in messages_data:
                    msg_id = msg_item["id"]
                    msg_res = requests.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                        headers=headers,
                        timeout=10
                    )
                    if msg_res.status_code != 200:
                        continue

                    msg_detail = msg_res.json()
                    payload = msg_detail.get("payload", {})
                    headers_list = payload.get("headers", [])

                    # Extract Headers
                    subject = "Complaint Email"
                    from_email = target_email
                    sender_name = "Customer"
                    email_date = None

                    for h in headers_list:
                        h_name = h.get("name", "").lower()
                        if h_name == "subject":
                            subject = h.get("value", subject)
                        elif h_name == "from":
                            raw_from = h.get("value", "")
                            # Parse "Name <email@domain>"
                            from_match = re.search(r'(?:"?([^"<]+)"?\s*)?<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>?', raw_from)
                            if from_match:
                                sender_name = from_match.group(1).strip() if from_match.group(1) else "Customer"
                                from_email = from_match.group(2).strip()
                            else:
                                from_email = re.sub(r'[<>\s"]', '', raw_from)
                        elif h_name == "date":
                            try:
                                import email.utils
                                parsed_tuple = email.utils.parsedate_tz(h.get("value", ""))
                                if parsed_tuple:
                                    email_date = datetime.utcfromtimestamp(email.utils.mktime_tz(parsed_tuple))
                            except Exception:
                                pass

                    # Extract Body and Attachments
                    body_text = ""
                    attachments = []
                    
                    def extract_parts(parts_list):
                        nonlocal body_text, attachments
                        for part in parts_list:
                            part_mime = part.get("mimeType", "")
                            part_body = part.get("body", {})
                            if part_mime == "text/plain" and "data" in part_body:
                                if not body_text:
                                    body_text = base64.urlsafe_b64decode(part_body["data"]).decode("utf-8", errors="ignore")
                            elif part_mime == "text/html" and "data" in part_body and not body_text:
                                html_raw = base64.urlsafe_b64decode(part_body["data"]).decode("utf-8", errors="ignore")
                                import re
                                body_text = re.sub(r'<[^>]+>', ' ', html_raw)
                            elif part_mime == "application/pdf" or str(part.get("filename", "")).lower().endswith(".pdf"):
                                attachment_id = part_body.get("attachmentId")
                                if attachment_id:
                                    try:
                                        att_res = requests.get(
                                            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/attachments/{attachment_id}",
                                            headers=headers,
                                            timeout=10
                                        )
                                        if att_res.status_code == 200:
                                            att_data = att_res.json().get("data", "")
                                            if att_data:
                                                file_data = base64.urlsafe_b64decode(att_data)
                                                attachments.append({
                                                    "filename": part.get("filename", "attachment.pdf"),
                                                    "mimeType": part_mime,
                                                    "content_bytes": file_data
                                                })
                                    except Exception as a_err:
                                        logger.error(f"[{self.agent_name}] Failed to fetch attachment: {a_err}")
                            if "parts" in part:
                                extract_parts(part["parts"])

                    if "parts" in payload:
                        extract_parts(payload["parts"])
                    elif "data" in payload.get("body", {}):
                        body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

                    if not body_text:
                        body_text = msg_detail.get("snippet", "Complaint body content.")
                    else:
                        import re
                        import html
                        # Remove style, script, and head blocks completely (avoid leaving raw CSS for the AI)
                        body_text = re.sub(r'<style[^>]*>.*?</style>', ' ', body_text, flags=re.DOTALL | re.IGNORECASE)
                        body_text = re.sub(r'<script[^>]*>.*?</script>', ' ', body_text, flags=re.DOTALL | re.IGNORECASE)
                        body_text = re.sub(r'<head[^>]*>.*?</head>', ' ', body_text, flags=re.DOTALL | re.IGNORECASE)
                        # Clean up any residual HTML tags
                        body_text = re.sub(r'<[^>]+>', ' ', body_text)
                        # Unescape HTML entities like &nbsp;
                        body_text = html.unescape(body_text)
                        # Clean up multiple spaces but PRESERVE newlines
                        body_text = re.sub(r'[ \t]+', ' ', body_text)
                        body_text = re.sub(r'\n\s*\n', '\n\n', body_text).strip()

                    # Determine whether this is a genuine banking dispute case first
                    if not classification_service.is_actual_dispute(from_email, subject, body_text):
                        logger.info(f"[{self.agent_name}] Skipping non-dispute email from {from_email}: {subject}")
                        # Mark email as read to prevent reprocessing
                        try:
                            requests.post(
                                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify",
                                headers=headers,
                                json={"removeLabelIds": ["UNREAD"]},
                                timeout=5
                            )
                        except Exception:
                            pass
                        continue

                    # Agentic intake: Rhea decides whether to call pdf_extract and extracts entities
                    from backend.app.services.intake_agent import intake_agent
                    intake = intake_agent.process(
                        email_body=body_text,
                        email_subject=subject,
                        sender_name=sender_name,
                        attachments=attachments,
                        fallback_amount=0.0,
                    )
                    entities = intake["entities"]
                    customer_name = entities["customer_name"]
                    account_no = entities.get("account_number") or ""
                    card_no = entities.get("card_number")
                    nric_val = entities.get("nric") or ""
                    amount_val = entities["amount"]

                    att_name = attachments[0]["filename"] if attachments else None

                    # Pass through the 5-Stage Agentic AI Pipeline
                    case_obj = intake_service.process_incoming_complaint(
                        customer_name=customer_name,
                        customer_email=from_email,
                        account_number=account_no,
                        nric=nric_val,
                        amount=amount_val,
                        email_subject=subject,
                        email_body=body_text,
                        attachment_name=att_name,
                        card_number=card_no,
                        received_at=email_date,
                        incident_date=entities.get("incident_date"),
                    )
                    session.add(case_obj)

                    # Write Gmail Sync Agent audit entry to audit_logs table
                    session.add(AuditLog(
                        case_id=case_obj.id,
                        actor="Gmail Sync Agent",
                        action="Complaint email ingested via Gmail OAuth API",
                        detail=f"From: {from_email} | Subject: {subject[:80]} | AI pipeline triggered",
                        created_at=datetime.utcnow(),
                    ))

                    synced_cases.append(case_obj.id)

                    # Mark email as read in Gmail (remove UNREAD label) ONLY AFTER SUCCESSFUL PROCESSING
                    try:
                        requests.post(
                            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify",
                            headers=headers,
                            json={"removeLabelIds": ["UNREAD"]},
                            timeout=5
                        )
                    except Exception as m_err:
                        logger.warning(f"[{self.agent_name}] Could not mark email {msg_id} as read: {m_err}")

                session.commit()

                return {
                    "status": "success",
                    "agent": self.agent_name,
                    "mailbox": target_email,
                    "synced_cases": synced_cases,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as err:
            logger.error(f"[{self.agent_name}] Exception in run_sync_cycle: {err}\n{traceback.format_exc()}")
            return {
                "status": "error",
                "message": str(err),
                "traceback": traceback.format_exc()
            }

    def run_sync_cycle_imap(self, creds: dict) -> dict:
        """
        Sync the Gmail complaints mailbox over IMAP using an app password.
        Fetches recent unread emails, filters for genuine banking disputes,
        and passes them through the 5-stage AI dispute pipeline.
        """
        import imaplib
        import re
        import email
        from email.header import decode_header
        import traceback as tb

        target_email = creds["email"]
        app_password = creds.get("app_password")
        max_emails = int(os.getenv("GMAIL_MAX_POLL", "3"))

        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(target_email, app_password)
            mail.select("INBOX")

            # Only fetch the most recent unread messages to avoid reprocessing thousands of old emails
            status, msg_ids = mail.search(None, "UNSEEN")
            all_ids = msg_ids[0].split() if msg_ids and msg_ids[0] else []
            if not all_ids:
                mail.logout()
                return {"status": "success", "mailbox": target_email, "synced_cases": [], "message": "Inbox clear. No unread complaints."}

            recent_ids = all_ids[-max_emails:]
            synced_cases = []

            with Session(engine) as session:
                for uid in recent_ids:
                    try:
                        status, msg_data = mail.fetch(uid, "(RFC822)")
                        if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                            continue
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)

                        subject = "Complaint Email"
                        from_email = target_email
                        sender_name = "Customer"
                        if msg["Subject"]:
                            decoded = decode_header(msg["Subject"])
                            subject = "".join(
                                part.decode(charset or "utf-8", errors="ignore") if isinstance(part, bytes) else part
                                for part, charset in decoded
                            )
                        if msg["From"]:
                            raw_from = msg["From"]
                            from_match = re.search(r'(?:"?([^"<]+)"?\s*)?<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>?', raw_from)
                            if from_match:
                                sender_name = from_match.group(1).strip() if from_match.group(1) else "Customer"
                                from_email = from_match.group(2).strip()

                        body_text = ""
                        attachments = []
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                fname = part.get_filename()
                                if ctype == "text/plain" and not fname:
                                    try:
                                        body_text = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                                        break
                                    except Exception:
                                        continue
                            # Second pass: collect attachments (PDF preferred) if body already filled
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                fname = part.get_filename()
                                if fname:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        attachments.append({
                                            "filename": fname,
                                            "mimeType": ctype,
                                            "content_bytes": payload,
                                        })
                        else:
                            try:
                                body_text = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
                            except Exception:
                                body_text = str(msg.get_payload())

                        if not body_text:
                            body_text = "Complaint body content."

                        # Filter genuine banking disputes
                        if not classification_service.is_actual_dispute(from_email, subject, body_text):
                            logger.info(f"[{self.agent_name}] Skipping non-dispute email from {from_email}: {subject}")
                            mail.store(uid, "+FLAGS", "\\Seen")
                            continue

                        # Agentic intake: Rhea decides whether to call pdf_extract and extracts entities
                        from backend.app.services.intake_agent import intake_agent
                        intake = intake_agent.process(
                            email_body=body_text,
                            email_subject=subject,
                            sender_name=sender_name,
                            attachments=attachments,
                            fallback_amount=1500.00,
                        )
                        entities = intake["entities"]
                        customer_name = entities["customer_name"]
                        account_no = entities["account_number"] or "114002938471"
                        card_no = entities["card_number"]
                        nric_val = entities["nric"] or "930214-08-5193"
                        amount_val = entities["amount"]

                        # 5-Stage AI Pipeline
                        pdf_att = next((a for a in attachments if a.get("mimeType") == "application/pdf" or str(a.get("filename", "")).lower().endswith(".pdf")), None)
                        case_obj = intake_service.process_incoming_complaint(
                            customer_name=customer_name,
                            customer_email=from_email,
                            account_number=account_no,
                            nric=nric_val,
                            amount=amount_val,
                            email_subject=subject,
                            email_body=body_text,
                            attachment_name=pdf_att.get("filename") if pdf_att else None,
                            card_number=card_no,
                        )
                        session.add(case_obj)

                        # Write Gmail Sync Agent audit entry to audit_logs table
                        tools_used = intake.get("used_tools") or []
                        session.add(AuditLog(
                            case_id=case_obj.id,
                            actor="Gmail Sync Agent",
                            action="Complaint email ingested via IMAP",
                            detail=(
                                f"From: {from_email} | Subject: {subject[:80]} | "
                                f"AI tools: {tools_used or 'none'} | Pipeline triggered"
                            ),
                            created_at=datetime.utcnow(),
                        ))

                        synced_cases.append(case_obj.id)
                        if tools_used:
                            logger.info(f"[{self.agent_name}] Rhea agent called tools: {tools_used} for {case_obj.id}")

                        # Mark as read ONLY after successful processing
                        mail.store(uid, "+FLAGS", "\\Seen")
                    except Exception as email_err:
                        logger.warning(f"[{self.agent_name}] IMAP processing error for msg: {email_err}")

                session.commit()

            mail.logout()
            return {
                "status": "success",
                "agent": self.agent_name,
                "mailbox": target_email,
                "method": "imap",
                "synced_cases": synced_cases,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as err:
            logger.error(f"[{self.agent_name}] IMAP sync error: {err}\n{tb.format_exc()}")
            return {"status": "error", "message": str(err), "traceback": tb.format_exc()}

    def start_background_sync_loop(self, interval_seconds: int = 30):
        """
        Starts an autonomous background poller thread.
        Periodically fetches DB refresh tokens, syncs complaints mailbox, and runs 5-stage AI pipeline.
        """
        import time
        import threading

        def _worker():
            logger.info(f"[{self.agent_name}] Autonomous Background Sync Worker initialized (Interval: {interval_seconds}s).")
            while True:
                time.sleep(interval_seconds)
                try:
                    self.run_sync_cycle()
                except Exception as e:
                    logger.error(f"[{self.agent_name}] Background sync error: {e}")

        thread = threading.Thread(target=_worker, daemon=True, name="GmailSyncAgentWorker")
        thread.start()

gmail_sync_agent = GmailSyncAgent()
