"""
email_alerts.py
Sends email alerts for new job matches.
Supports:
  - Immediate single alert
  - Scheduled periodic alerts (using 'schedule' library)
  - Gmail SMTP (with App Password) or any SMTP server
"""

import os
import smtplib
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict
import schedule


# ── Config from environment ──────────────────────────────────────────

SMTP_HOST      = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL   = os.getenv("ALERT_EMAIL_SENDER", "")
SENDER_PASS    = os.getenv("ALERT_EMAIL_PASSWORD", "")
RECIPIENT      = os.getenv("ALERT_EMAIL_RECIPIENT", "")


# ── Email builder ────────────────────────────────────────────────────

def _build_html(jobs_text: str, profile_summary: str) -> str:
    """Render a clean HTML email body."""
    date_str = datetime.now().strftime("%B %d, %Y")
    rows = ""
    for block in jobs_text.split("---"):
        block = block.strip()
        if block:
            rows += f"<div style='margin-bottom:20px;padding:16px;border-left:4px solid #4F46E5;background:#F9FAFB;border-radius:4px;'>{block.replace(chr(10),'<br>')}</div>"

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;color:#1F2937;">
      <div style="background:#4F46E5;padding:24px;border-radius:8px 8px 0 0;">
        <h1 style="color:white;margin:0;font-size:22px;">🔍 New Job Matches – {date_str}</h1>
        <p style="color:#C7D2FE;margin:8px 0 0;">Profile: {profile_summary}</p>
      </div>
      <div style="padding:24px;background:#fff;border-radius:0 0 8px 8px;border:1px solid #E5E7EB;">
        <p style="color:#6B7280;">Here are your latest job matches found by the AI Job Search Agent:</p>
        {rows}
        <hr style="border:none;border-top:1px solid #E5E7EB;margin:24px 0;">
        <p style="color:#9CA3AF;font-size:12px;">
          You are receiving this because you set up job alerts. 
          To stop alerts, update your preferences in the app.
        </p>
      </div>
    </body></html>
    """


# ── Core send function ───────────────────────────────────────────────

def send_job_alert(
    jobs_text: str,
    profile_summary: str,
    recipient: str = None,
    subject: str = None
) -> tuple[bool, str]:
    """
    Send a job alert email.

    Args:
        jobs_text:       Formatted job results string.
        profile_summary: Short summary of the user profile (for email header).
        recipient:       Override ALERT_EMAIL_RECIPIENT env var.
        subject:         Custom subject line.

    Returns:
        (success: bool, message: str)
    """
    to_addr = recipient or RECIPIENT
    if not to_addr:
        return False, "No recipient email configured."
    if not SENDER_EMAIL or not SENDER_PASS:
        return False, "Sender email credentials not configured (check .env)."

    subject = subject or f"🔍 New Job Matches – {datetime.now().strftime('%B %d, %Y')}"
    html    = _build_html(jobs_text, profile_summary)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = to_addr
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.sendmail(SENDER_EMAIL, to_addr, msg.as_string())
        return True, f"Alert sent to {to_addr}"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP Authentication failed. Check email/password in .env."
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"


# ── Scheduled alerts ─────────────────────────────────────────────────

class JobAlertScheduler:
    """
    Background scheduler that re-runs the job search and emails
    new results at a specified interval.
    """

    def __init__(self):
        self._thread  = None
        self._running = False
        self._job     = None

    def start(
        self,
        search_fn,           # Callable[[], str] — returns jobs_text
        profile_summary: str,
        recipient: str,
        interval_hours: int = 24
    ):
        """Start periodic job alerts."""
        if self._running:
            self.stop()

        def job():
            jobs_text = search_fn()
            if jobs_text:
                send_job_alert(jobs_text, profile_summary, recipient)

        schedule.clear("job-alert")
        schedule.every(interval_hours).hours.do(job).tag("job-alert")
        self._running = True

        def run():
            while self._running:
                schedule.run_pending()
                time.sleep(60)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scheduled alerts."""
        self._running = False
        schedule.clear("job-alert")

    @property
    def is_running(self) -> bool:
        return self._running


# Singleton scheduler instance
alert_scheduler = JobAlertScheduler()
