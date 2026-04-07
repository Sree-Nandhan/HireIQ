"""
Sends OTP emails via SMTP.

Falls back to logging the OTP to the console when SMTP is not configured —
useful for local dev / demos where you can see it in `docker logs`.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from api.config import settings

logger = logging.getLogger(__name__)


def _sanitize_email(to_email: str) -> str:
    """Reject emails containing CRLF or null bytes to prevent header injection."""
    for ch in ("\n", "\r", "\0"):
        if ch in to_email:
            raise ValueError(f"Invalid email address: contains forbidden character {ch!r}")
    return to_email.strip()


def send_otp_email(to_email: str, otp: str) -> None:
    """Send a sign-in OTP to *to_email*.

    If SMTP is not configured (smtp_user is empty), the OTP is printed to the
    server log so development / demo flows still work without email credentials.
    """
    to_email = _sanitize_email(to_email)

    if not settings.smtp_user:
        logger.warning(
            "SMTP not configured — OTP for %s is: %s  (expires in %d min)",
            to_email,
            otp,
            settings.otp_expire_minutes,
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your HireIQ sign-in code"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email

    plain = (
        f"Your HireIQ sign-in code is: {otp}\n\n"
        f"This code expires in {settings.otp_expire_minutes} minutes and can only be used once."
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:40px auto;padding:32px;
                border:1px solid #e5e7eb;border-radius:12px">
      <h2 style="color:#6366f1;margin-top:0">HireIQ</h2>
      <p style="color:#374151">Use the code below to sign in to your account:</p>
      <div style="font-size:40px;font-weight:700;letter-spacing:10px;
                  color:#1e1e2e;padding:24px 0;text-align:center">{otp}</div>
      <p style="color:#6b7280;font-size:14px">
        This code expires in <strong>{settings.otp_expire_minutes} minutes</strong>
        and can only be used once. If you didn't request this, you can safely ignore it.
      </p>
    </div>
    """

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(msg["From"], to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(msg["From"], to_email, msg.as_string())
        logger.info("OTP email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        raise
