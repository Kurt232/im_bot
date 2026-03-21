"""Tests for im_bot_email.replier."""

from unittest.mock import MagicMock, patch

from im_bot_email.executor import TaskResult
from im_bot_email.parser import ParsedEmail
from im_bot_email.replier import _build_body, _build_message, send_reply


def _make_parsed(**kwargs):
    defaults = dict(subject="Test task", sender="alice@example.com", body="do something")
    defaults.update(kwargs)
    return ParsedEmail(**defaults)


# --- _build_body ---


def test_build_body_success():
    result = TaskResult(return_code=0, stdout="hello world", stderr="")
    body = _build_body(result)
    assert body.startswith("[OK]")
    assert "hello world" in body
    assert "stderr" not in body


def test_build_body_failure():
    result = TaskResult(return_code=1, stdout="", stderr="something broke")
    body = _build_body(result)
    assert "[FAIL]" in body
    assert "code 1" in body
    assert "something broke" in body
    assert "stdout" not in body


def test_build_body_both_streams():
    result = TaskResult(return_code=0, stdout="out", stderr="warn")
    body = _build_body(result)
    assert "--- stdout ---" in body
    assert "--- stderr ---" in body


def test_build_body_empty_output():
    result = TaskResult(return_code=0, stdout="", stderr="")
    body = _build_body(result)
    assert body == "[OK] Task completed successfully."


# --- _build_message ---


def test_build_message_subject_prefix():
    msg = _build_message(_make_parsed(), TaskResult(0, "", ""), "bot@example.com")
    assert msg["Subject"] == "Re: Test task"


def test_build_message_no_double_re():
    msg = _build_message(
        _make_parsed(subject="Re: already"), TaskResult(0, "", ""), "bot@example.com"
    )
    assert msg["Subject"] == "Re: already"


def test_build_message_headers():
    parsed = _make_parsed(sender="alice@example.com")
    msg = _build_message(parsed, TaskResult(0, "ok", ""), "bot@example.com")
    assert msg["From"] == "bot@example.com"
    assert msg["To"] == "alice@example.com"


# --- send_reply ---


def test_send_reply_skips_when_no_host():
    """Should silently skip when SMTP_HOST is empty."""
    send_reply(
        _make_parsed(),
        TaskResult(0, "", ""),
        smtp_host="",
        smtp_port=465,
        email_user="bot@example.com",
        email_password="secret",
    )
    # No exception raised — just returns.


@patch("im_bot_email.replier.smtplib.SMTP_SSL")
def test_send_reply_connects_and_sends(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reply(
        _make_parsed(sender="alice@example.com"),
        TaskResult(0, "done", ""),
        smtp_host="smtp.example.com",
        smtp_port=465,
        email_user="bot@example.com",
        email_password="secret",
    )

    mock_smtp_cls.assert_called_once_with("smtp.example.com", 465)
    mock_server.login.assert_called_once_with("bot@example.com", "secret")
    mock_server.send_message.assert_called_once()

    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg["To"] == "alice@example.com"
    assert sent_msg["Subject"] == "Re: Test task"


@patch("im_bot_email.replier.smtplib.SMTP_SSL")
def test_send_reply_message_contains_result(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reply(
        _make_parsed(),
        TaskResult(1, "partial output", "error details"),
        smtp_host="smtp.example.com",
        smtp_port=465,
        email_user="bot@example.com",
        email_password="secret",
    )

    sent_msg = mock_server.send_message.call_args[0][0]
    payload = sent_msg.get_payload(decode=True).decode()
    assert "[FAIL]" in payload
    assert "partial output" in payload
    assert "error details" in payload
