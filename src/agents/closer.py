import asyncio
import base64
import os
import json
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "astystudio@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
DB_PATH = "nexusai_sent.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT, contact_email TEXT, subject TEXT,
            message_id TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            winner_variant TEXT, winner_score REAL
        )
    """)
    conn.commit()
    conn.close()

async def run_closer_agent(contact: dict, email_content: dict, profile: dict, log_fn=None) -> dict:
    """Embed HTML card in Gmail and send. Track in SQLite."""
    
    init_db()
    to_email = contact.get("email")
    subject = email_content.get("best_subject", "Quick question")
    body_text = email_content.get("best_email", "")
    html_card = email_content.get("html_card", "")
    
    if log_fn:
        await log_fn(f"📤 Closer: Preparing email to {to_email} with visual card embedded...")
    
    # Build MIME email with HTML card embedded inline
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = to_email
    msg["From"] = SENDER_EMAIL
    
    # Plain text fallback
    text_part = MIMEText(body_text, "plain")
    
    # HTML part — email body + embedded visual card
    html_body = f"""<!DOCTYPE html>
<html>
<body style="background-color:#0a0a09;margin:0;padding:20px;font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:600px;margin:0 auto;">
    
    <!-- Email body text -->
    <div style="color:#d4d0c8;font-size:14px;line-height:1.8;margin-bottom:32px;">
      {body_text.replace(chr(10), '<br>')}
    </div>
    
    <!-- Visual intelligence card -->
    <div style="margin-top:24px;">
      {html_card}
    </div>
    
    <!-- Footer -->
    <div style="margin-top:24px;font-size:11px;color:#555550;border-top:1px solid #1c1c19;padding-top:16px;">
      NexusAI Intelligence Report | 
      <a href="https://calendly.com/nexusai" style="color:#00e88f;text-decoration:none;">Book a call</a>
    </div>
    
  </div>
</body>
</html>"""
    
    html_part = MIMEText(html_body, "html")
    msg.attach(text_part)
    msg.attach(html_part)
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    try:
        if not GMAIL_APP_PASSWORD:
            if log_fn:
                await log_fn("⚠️ Closer: GMAIL_APP_PASSWORD not set in .env — cannot send. Set it to enable email sending.")
            return {"sent": False, "error": "GMAIL_APP_PASSWORD not configured. See .env instructions."}

        # Send via SMTP (no OAuth needed — uses Gmail App Password)
        def _send_smtp():
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
                server.send_message(msg)

        await asyncio.to_thread(_send_smtp)
        message_id = f"smtp_{hash(raw) % 100000}"
        
        # Track in SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO sent_emails (company, contact_email, subject, message_id, winner_variant, winner_score) VALUES (?,?,?,?,?,?)",
            (
                profile.get("company_name"), to_email, subject, message_id,
                email_content.get("winner"),
                email_content.get(f"score_{email_content.get('winner', 'b')}", {}).get("total", 0)
            )
        )
        conn.commit()
        conn.close()
        
        if log_fn:
            await log_fn(f"✅ Closer: Email sent! Message ID: {message_id} | Check inbox now.")
        
        return {"sent": True, "message_id": message_id, "to": to_email}
        
    except Exception as e:
        if log_fn:
            await log_fn(f"❌ Closer: Send failed — {str(e)}")
        return {"sent": False, "error": str(e)}
