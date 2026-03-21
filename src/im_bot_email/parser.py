"""Email parser — extract subject, body, attachments from an email.message.Message."""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from email.header import decode_header
from email.message import Message

logger = logging.getLogger(__name__)


@dataclass
class Attachment:
    """A single email attachment."""

    filename: str
    content: bytes
    content_type: str


@dataclass
class ParsedEmail:
    """Structured representation of an incoming email."""

    subject: str
    sender: str
    body: str
    attachments: list[Attachment] = field(default_factory=list)

    def to_task_description(self) -> str:
        """Format the email as a plain-text task description for TASK_COMMAND."""
        parts = [f"Subject: {self.subject}", f"From: {self.sender}", "", self.body]
        if self.attachments:
            names = ", ".join(a.filename for a in self.attachments)
            parts.append(f"\n[Attachments: {names}]")
        return "\n".join(parts)


def _decode_header_value(raw: str | None) -> str:
    """Decode an RFC 2047 encoded header into a plain string."""
    if not raw:
        return ""
    parts: list[str] = []
    for fragment, charset in decode_header(raw):
        if isinstance(fragment, bytes):
            parts.append(fragment.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(fragment)
    return "".join(parts)


def _strip_html(text: str) -> str:
    """Crude HTML→plain-text conversion: strip tags, decode entities."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _get_body(msg: Message) -> str:
    """Extract the best plain-text body from a MIME message."""
    if not msg.is_multipart():
        ct = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload is None:
            return ""
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if ct == "text/html":
            return _strip_html(text)
        return text.strip()

    # Walk multipart: prefer text/plain, fall back to text/html.
    plain: str | None = None
    html_body: str | None = None

    for part in msg.walk():
        ct = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="replace")
        if ct == "text/plain" and plain is None:
            plain = decoded.strip()
        elif ct == "text/html" and html_body is None:
            html_body = decoded

    if plain:
        return plain
    if html_body:
        return _strip_html(html_body)
    return ""


def _get_attachments(msg: Message) -> list[Attachment]:
    """Extract file attachments from a MIME message."""
    attachments: list[Attachment] = []
    if not msg.is_multipart():
        return attachments

    for part in msg.walk():
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" not in disposition:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        filename = part.get_filename() or "unnamed"
        filename = _decode_header_value(filename)
        ct = part.get_content_type() or "application/octet-stream"
        attachments.append(Attachment(filename=filename, content=payload, content_type=ct))
        logger.debug("Attachment: %s (%s, %d bytes)", filename, ct, len(payload))

    return attachments


def parse_email(msg: Message) -> ParsedEmail:
    """Parse an email.message.Message into a ParsedEmail."""
    return ParsedEmail(
        subject=_decode_header_value(msg.get("Subject")),
        sender=_decode_header_value(msg.get("From")),
        body=_get_body(msg),
        attachments=_get_attachments(msg),
    )
