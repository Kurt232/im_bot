"""Replier — send task results back to the original sender."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.utils import parseaddr

from .executor import TaskResult
from .parser import ParsedEmail

logger = logging.getLogger(__name__)

# Pattern: a line that starts with FILE: followed by a path.
_FILE_LINE_RE = re.compile(r"^FILE:\s*(.+)$", re.MULTILINE)

# Addresses that should never receive automated replies.
_NOREPLY_PATTERNS = (
    "noreply", "no-reply", "no_reply",
    "mailer-daemon", "postmaster",
    "accountprotection.microsoft.com",
    "bounce", "undeliverable",
)


def extract_file_paths(stdout: str) -> list[str]:
    """Extract file paths from FILE: lines in stdout.

    Returns only paths that point to existing files.
    """
    paths = []
    for match in _FILE_LINE_RE.finditer(stdout):
        path = match.group(1).strip()
        if os.path.isfile(path):
            paths.append(path)
        else:
            logger.warning("FILE: path does not exist, skipping: %s", path)
    return paths


def _strip_file_lines(stdout: str) -> str:
    """Remove FILE: lines from stdout so they don't appear in the body."""
    return _FILE_LINE_RE.sub("", stdout).strip()


def _build_body(result: TaskResult) -> str:
    """Format a TaskResult into a human-readable reply body."""
    lines: list[str] = []

    if result.success:
        lines.append("[OK] Task completed successfully.")
    else:
        lines.append(f"[FAIL] Task exited with code {result.return_code}.")

    stdout_clean = _strip_file_lines(result.stdout) if result.stdout else ""

    if stdout_clean:
        lines.append("")
        lines.append("--- stdout ---")
        lines.append(stdout_clean)

    if result.stderr:
        lines.append("")
        lines.append("--- stderr ---")
        lines.append(result.stderr.rstrip())

    return "\n".join(lines)


def _build_message(
    parsed: ParsedEmail,
    result: TaskResult,
    from_addr: str,
) -> MIMEBase:
    """Build a reply message, with file attachments if FILE: lines are present."""
    body = _build_body(result)
    file_paths = extract_file_paths(result.stdout) if result.stdout else []

    if not file_paths:
        msg = MIMEText(body, "plain", "utf-8")
    else:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))
        for fpath in file_paths:
            ctype, _ = mimetypes.guess_type(fpath)
            if ctype is None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            part = MIMEBase(maintype, subtype)
            with open(fpath, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(fpath),
            )
            msg.attach(part)
            logger.info("Attached file: %s", fpath)

    subject = parsed.subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = parsed.sender

    return msg


def _should_skip_reply(sender: str) -> bool:
    """Return True if we should not reply to this sender."""
    _, addr = parseaddr(sender)
    addr_lower = addr.lower() if addr else sender.lower()
    return any(p in addr_lower for p in _NOREPLY_PATTERNS)


def _send_via_graph(parsed: ParsedEmail, result: TaskResult, oauth2_manager) -> None:
    """Send reply via Microsoft Graph API — bypasses SMTP entirely."""
    import requests as http_requests

    token = oauth2_manager.get_graph_token()
    body_text = _build_body(result)

    subject = parsed.subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    _, recipient = parseaddr(parsed.sender)
    if not recipient:
        recipient = parsed.sender

    message: dict = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body_text},
        "toRecipients": [{"emailAddress": {"address": recipient}}],
    }

    file_paths = extract_file_paths(result.stdout) if result.stdout else []
    if file_paths:
        attachments = []
        for fpath in file_paths:
            with open(fpath, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            attachments.append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(fpath),
                "contentBytes": content,
            })
            logger.info("Attached file: %s", fpath)
        message["attachments"] = attachments

    resp = http_requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"message": message},
        timeout=30,
    )
    if not resp.ok:
        logger.error("Graph API error %d: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    logger.info("Reply sent via Graph API to %s", recipient)


def send_reply(
    parsed: ParsedEmail,
    result: TaskResult,
    *,
    smtp_host: str,
    smtp_port: int,
    email_user: str,
    email_password: str,
    oauth2_manager=None,
) -> None:
    """Send a reply email with the task result to the original sender."""
    if _should_skip_reply(parsed.sender):
        logger.info("Skipping reply to no-reply address: %s", parsed.sender)
        return

    # OAuth2: use Microsoft Graph API (SMTP AUTH is disabled on Outlook.com).
    if oauth2_manager is not None:
        _send_via_graph(parsed, result, oauth2_manager)
        return

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

    if smtp_port == 587:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(email_user, email_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(email_user, email_password)
            server.send_message(msg)

    logger.info("Reply sent successfully")
