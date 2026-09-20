import os
import smtplib
from email.message import EmailMessage


def send_email(to_address: str, subject: str, body: str) -> str:
    """
    Send an email via the local Mailpit SMTP server (or configured SMTP server).
    """
    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "1025"))
    from_address = os.getenv("SMTP_FROM", "agent@forge.local")

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.send_message(msg)
        return f"Email successfully sent to {to_address} with subject '{subject}'"
    except (smtplib.SMTPException, OSError) as e:
        return f"Failed to send email: {e!s}"
