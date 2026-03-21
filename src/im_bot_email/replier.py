"""SMTP replier — send task results back to the original sender."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from .executor import TaskResult
from .parser import ParsedEmail

logger = logging.getLogger(__name__)


def _build_body(result: TaskResult) -> str:
    """Format a TaskResult into a human-readable reply body."""
    lines: list[str] = []

    if result.success:
        lines.append("[OK] Task completed successfully.")
    else:
        lines.append(f"[FAIL] Task exited with code {result.return_code}.")

    if result.stdout:
        lines.append("")
        lines.append("--- stdout ---")
        lines.append(result.stdout.rstrip())

    if result.stderr:
        lines.append("")
        lines.append("--- stderr ---")
        lines.append(result.stderr.rstrip())

    return "\n".join(lines)


def _build_message(
    parsed: ParsedEmail,
    result: TaskResult,
    from_addr: str,
) -> MIMEText:
    """Build a MIMEText reply message."""
    body = _build_body(result)
    msg = MIMEText(body, "plain", "utf-8")

    subject = parsed.subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = parsed.sender

    return msg


def send_reply(
    parsed: ParsedEmail,
    result: TaskResult,
    *,
    smtp_host: str,
    smtp_port: int,
    email_user: str,
    email_password: str,
) -> None:
    """Send a reply email with the task result to the original sender.

    Uses SMTP_SSL (implicit TLS) which is the standard for port 465.
    """
    if not smtp_host:
        logger.warning("SMTP_HOST not configured, skipping reply")
        return

    msg = _build_message(parsed, result, from_addr=email_user)

    logger.info(
        "Sending reply to %s via %s:%d (subject=%r)",
        parsed.sender,
        smtp_host,
        smtp_port,
        msg["Subject"],
    )

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(email_user, email_password)
        server.send_message(msg)

    logger.info("Reply sent successfully")
