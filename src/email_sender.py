"""
src/email_sender.py

Optional email-sending feature using Python's built-in smtplib.
This module is entirely independent of research/scoring/email generation -
if SMTP isn't configured, the rest of the app still works fine.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

from utils.helpers import is_configured

SMTP_ENV_VARS = ["SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]


def is_email_sending_configured() -> bool:
    """Check whether all required SMTP environment variables are set."""
    return is_configured(*SMTP_ENV_VARS)


def send_email(to_email: str, subject: str, body: str) -> Tuple[bool, str]:
    """
    Send a single email via SMTP (e.g. Gmail).

    Returns (success, message) instead of raising, so the Streamlit UI can
    show a clean success/error message.
    """
    if not is_email_sending_configured():
        return False, (
            "Email sending is not configured. Set SMTP_SERVER, SMTP_PORT, "
            "SMTP_USERNAME, and SMTP_PASSWORD in your .env or Streamlit secrets."
        )

    if not to_email or "@" not in to_email:
        return False, "Cannot send: no valid recipient email address is available for this lead."

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    message = MIMEMultipart()
    message["From"] = smtp_username
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, to_email, message.as_string())
        return True, f"Email sent successfully to {to_email}."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check SMTP_USERNAME/SMTP_PASSWORD (use an app password for Gmail)."
    except smtplib.SMTPException as e:
        return False, f"Failed to send email: {e}"
    except Exception as e:
        return False, f"Unexpected error while sending email: {e}"
