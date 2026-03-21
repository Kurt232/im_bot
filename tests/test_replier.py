"""Tests for im_bot_email.replier."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from im_bot_email.executor import TaskResult
from im_bot_email.parser import ParsedEmail
from im_bot_email.replier import (
    _build_body,
    _build_message,
    _strip_file_lines,
    extract_file_paths,
    send_reply,
)


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


# --- extract_file_paths ---


def test_extract_file_paths_finds_existing_files():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"hello")
        path = f.name
    try:
        stdout = f"some output\nFILE: {path}\nmore output"
        paths = extract_file_paths(stdout)
        assert paths == [path]
    finally:
        os.unlink(path)


def test_extract_file_paths_skips_nonexistent():
    stdout = "FILE: /nonexistent/path/foo.txt\n"
    paths = extract_file_paths(stdout)
    assert paths == []


def test_extract_file_paths_multiple():
    with tempfile.NamedTemporaryFile(suffix=".a", delete=False) as f1, \
         tempfile.NamedTemporaryFile(suffix=".b", delete=False) as f2:
        f1.write(b"a")
        f2.write(b"b")
    try:
        stdout = f"FILE: {f1.name}\nstuff\nFILE: {f2.name}\n"
        paths = extract_file_paths(stdout)
        assert paths == [f1.name, f2.name]
    finally:
        os.unlink(f1.name)
        os.unlink(f2.name)


def test_extract_file_paths_empty_stdout():
    assert extract_file_paths("") == []
    assert extract_file_paths("no file lines here") == []


# --- _strip_file_lines ---


def test_strip_file_lines():
    stdout = "line1\nFILE: /some/path\nline2"
    assert _strip_file_lines(stdout) == "line1\n\nline2"


def test_strip_file_lines_no_file_lines():
    assert _strip_file_lines("just normal output") == "just normal output"


# --- _build_body with FILE: lines ---


def test_build_body_strips_file_lines():
    result = TaskResult(return_code=0, stdout="output\nFILE: /tmp/foo.txt\nmore", stderr="")
    body = _build_body(result)
    assert "FILE:" not in body
    assert "output" in body
    assert "more" in body


# --- _build_message with attachments ---


def test_build_message_no_attachments_returns_mime_text():
    msg = _build_message(_make_parsed(), TaskResult(0, "plain output", ""), "bot@example.com")
    assert msg.get_content_type() == "text/plain"


def test_build_message_with_attachment_returns_multipart():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"file content")
        path = f.name
    try:
        result = TaskResult(0, f"result\nFILE: {path}\n", "")
        msg = _build_message(_make_parsed(), result, "bot@example.com")
        assert msg.get_content_type() == "multipart/mixed"
        parts = msg.get_payload()
        assert len(parts) == 2
        # First part is the text body
        assert parts[0].get_content_type() == "text/plain"
        body = parts[0].get_payload(decode=True).decode()
        assert "[OK]" in body
        assert "FILE:" not in body
        # Second part is the attachment
        assert parts[1].get_content_type() == "text/plain"
        assert parts[1].get_filename() == os.path.basename(path)
    finally:
        os.unlink(path)


@patch("im_bot_email.replier.smtplib.SMTP")
def test_send_reply_starttls_on_port_587(mock_smtp_cls):
    """Port 587 should use SMTP + STARTTLS (Outlook)."""
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    send_reply(
        _make_parsed(sender="alice@example.com"),
        TaskResult(0, "done", ""),
        smtp_host="smtp-mail.outlook.com",
        smtp_port=587,
        email_user="bot@outlook.com",
        email_password="secret",
    )

    mock_smtp_cls.assert_called_once_with("smtp-mail.outlook.com", 587)
    mock_server.ehlo.assert_called()
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("bot@outlook.com", "secret")
    mock_server.send_message.assert_called_once()


@patch("im_bot_email.replier.smtplib.SMTP_SSL")
def test_send_reply_with_attachment(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        f.write(b"col1,col2\na,b\n")
        path = f.name
    try:
        send_reply(
            _make_parsed(),
            TaskResult(0, f"done\nFILE: {path}\n", ""),
            smtp_host="smtp.example.com",
            smtp_port=465,
            email_user="bot@example.com",
            email_password="secret",
        )
        mock_server.send_message.assert_called_once()
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg.get_content_type() == "multipart/mixed"
    finally:
        os.unlink(path)
