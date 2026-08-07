import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_dispute_email(to_email, sender_email, app_password):
    """
    Sends a real banking complaint email to the specified target Gmail inbox.
    """
    subject = "URGENT DISPUTE: Unauthorized Debit Card Transaction of RM 1,500.00"
    body = f"""Dear AduanFlow Bank Support Team,

I am writing to formally log a banking dispute regarding an unauthorized transaction of RM 1,500.00 deducted from my savings account 114002938471 (NRIC: 040125-01-0509) on 1st August 2026.

I did not authorize or perform this payment. Please initiate an immediate fraud investigation, freeze the card exposure, and issue a full credit reversal.

Target Inbox: {to_email}
Account Number: 114002938471
Dispute Amount: RM 1,500.00

Thank you,
Gan Yao Tong
"""

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        print(f"Connecting to Gmail SMTP server (smtp.gmail.com:587)...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        print(f"Authenticating as {sender_email}...")
        server.login(sender_email, app_password)
        print(f"Sending dispute email to {to_email}...")
        server.send_message(msg)
        server.quit()
        print(f"\nSUCCESS: Real dispute email delivered to {to_email}!")
    except Exception as e:
        print(f"\nSMTP ERROR: Failed to send email via Google SMTP: {e}")
        print("\nTip: Gmail requires a 16-character App Password when sending via SMTP.")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else "ganyaotong@graduate.utm.my"
    sender = sys.argv[2] if len(sys.argv) > 2 else None
    passwd = sys.argv[3] if len(sys.argv) > 3 else None

    if not sender or not passwd:
        print("Usage: python backend/scripts/send_real_email.py <TO_EMAIL> <SENDER_GMAIL> <SENDER_APP_PASSWORD>")
        print(f"Example: python backend/scripts/send_real_email.py {target} myemail@gmail.com xxxx-yyyy-zzzz-aaaa")
    else:
        send_dispute_email(target, sender, passwd)
