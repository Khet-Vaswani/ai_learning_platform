# ============================================================
# mailer.py — Send email through any SMTP server (e.g. Gmail)
# Configure with SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM.
# ============================================================

import os
import smtplib
from email.message import EmailMessage


def mail_configured() -> bool:
    return bool(os.getenv('SMTP_HOST'))


def send_email(to: str, subject: str, text: str) -> bool:
    """Send a plain-text email. Returns False (and logs why) if it couldn't be sent."""
    host = os.getenv('SMTP_HOST')
    if not host:
        return False
    port     = int(os.getenv('SMTP_PORT', 587))
    user     = os.getenv('SMTP_USER', '')
    password = os.getenv('SMTP_PASSWORD', '')

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = os.getenv('MAIL_FROM') or user
    msg['To']      = to
    msg.set_content(text)

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            if server.has_extn('starttls'):
                server.starttls()
                server.ehlo()
        with server:
            if user:
                server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[MAIL] Could not send '{subject}': {type(e).__name__}: {e}")
        return False
