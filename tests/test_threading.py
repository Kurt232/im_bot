"""Tests for email threading (In-Reply-To / References headers)."""

from email.mime.text import MIMEText

from im_bot_email.parser import parse_email
from im_bot_email.replier import _build_message
from im_bot_email.executor import TaskResult


def _make_msg(message_id=None, references=None):
    msg = MIMEText("Hello")
    msg["Subject"] = "Test"
    msg["From"] = "alice@example.com"
    msg["To"] = "bot@example.com"
    if message_id:
        msg["Message-ID"] = message_id
    if references:
        msg["References"] = references
    return msg


def _ok_result():
    return TaskResult(return_code=0, stdout="done", stderr="")


def test_parse_message_id():
    parsed = parse_email(_make_msg(message_id="<abc123@example.com>"))
    assert parsed.message_id == "<abc123@example.com>"


def test_parse_references():
    parsed = parse_email(_make_msg(
        message_id="<msg2@example.com>",
        references="<msg1@example.com>",
    ))
    assert parsed.references == "<msg1@example.com>"


def test_parse_no_message_id():
    parsed = parse_email(_make_msg())
    assert parsed.message_id == ""
    assert parsed.references == ""


def test_reply_sets_in_reply_to():
    parsed = parse_email(_make_msg(message_id="<abc@example.com>"))
    reply = _build_message(parsed, _ok_result(), "bot@example.com")
    assert reply["In-Reply-To"] == "<abc@example.com>"


def test_reply_sets_references_from_message_id():
    parsed = parse_email(_make_msg(message_id="<abc@example.com>"))
    reply = _build_message(parsed, _ok_result(), "bot@example.com")
    assert reply["References"] == "<abc@example.com>"


def test_reply_appends_to_existing_references():
    parsed = parse_email(_make_msg(
        message_id="<msg2@example.com>",
        references="<msg1@example.com>",
    ))
    reply = _build_message(parsed, _ok_result(), "bot@example.com")
    assert reply["References"] == "<msg1@example.com> <msg2@example.com>"


def test_reply_no_threading_without_message_id():
    parsed = parse_email(_make_msg())
    reply = _build_message(parsed, _ok_result(), "bot@example.com")
    assert reply["In-Reply-To"] is None
    assert reply["References"] is None
