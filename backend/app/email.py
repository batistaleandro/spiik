"""SMTP email sending for the password recovery flow.

Configured entirely through environment variables — no keys or paid
services are required, any plain SMTP account works:

- ``SPIIK_SMTP_HOST`` / ``SPIIK_SMTP_PORT`` (default 587; use 465 for implicit TLS)
- ``SPIIK_SMTP_USER`` / ``SPIIK_SMTP_PASSWORD`` (optional auth)
- ``SPIIK_SMTP_FROM`` (default ``spiik@localhost``)
- ``SPIIK_APP_URL`` (base URL used in the reset link, default ``http://localhost:8900``)

Without ``SPIIK_SMTP_HOST`` nothing is sent; the reset link is written to
the server log instead, which keeps local development usable.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("spiik.email")

RESET_LINK_TTL_HOURS = 1


def send_password_reset_email(to: str, token: str) -> None:
    """Deliver the one-time reset link. Failures are logged, never raised —
    the endpoint must not leak whether (or how) an email went out."""
    base = os.environ.get("SPIIK_APP_URL", "http://localhost:8900").rstrip("/")
    link = f"{base}/reset-password?token={token}"
    host = os.environ.get("SPIIK_SMTP_HOST")
    if not host:
        logger.warning(
            "SPIIK_SMTP_HOST is not set — password reset link for %s: %s", to, link
        )
        return

    msg = EmailMessage()
    msg["From"] = os.environ.get("SPIIK_SMTP_FROM", "spiik@localhost")
    msg["To"] = to
    msg["Subject"] = "Reset your spiik password"
    msg.set_content(
        "Someone asked to reset your spiik password.\n\n"
        f"Open this link to choose a new one (valid for {RESET_LINK_TTL_HOURS} hour):\n"
        f"{link}\n\n"
        "If this wasn't you, ignore this email — your password stays unchanged."
    )

    port = int(os.environ.get("SPIIK_SMTP_PORT", "587"))
    user = os.environ.get("SPIIK_SMTP_USER")
    password = os.environ.get("SPIIK_SMTP_PASSWORD")
    try:
        if port == 465:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            smtp = smtplib.SMTP(host, port, timeout=15)
        with smtp:
            if port != 465 and smtp.has_extn("starttls"):
                smtp.starttls()
            if user:
                smtp.login(user, password or "")
            smtp.send_message(msg)
    except Exception:
        logger.exception("failed to send password reset email to %s", to)
