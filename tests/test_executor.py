"""Tests for task executor."""

import os

from im_bot_email.executor import execute_task, TaskResult
from im_bot_email.parser import Attachment, ParsedEmail


def _make_parsed(subject="Test", sender="a@b.com", body="hello", attachments=None):
    return ParsedEmail(
        subject=subject,
        sender=sender,
        body=body,
        attachments=attachments or [],
    )


def test_echo_command():
    """Default TASK_COMMAND='echo' just echoes stdin — verify basic flow."""
    parsed = _make_parsed(body="do the thing")
    result = execute_task(parsed, "echo ok")
    assert result.success
    assert result.return_code == 0
    assert "ok" in result.stdout


def test_stdin_received():
    """Command receives the task description on stdin."""
    parsed = _make_parsed(subject="Buy milk", sender="user@x.com", body="2 litres")
    result = execute_task(parsed, "cat")
    assert result.success
    assert "Subject: Buy milk" in result.stdout
    assert "From: user@x.com" in result.stdout
    assert "2 litres" in result.stdout


def test_failing_command():
    """Non-zero exit code is captured."""
    parsed = _make_parsed()
    result = execute_task(parsed, "exit 42")
    assert not result.success
    assert result.return_code == 42


def test_stderr_captured():
    """Standard error output is captured."""
    parsed = _make_parsed()
    result = execute_task(parsed, "echo oops >&2; exit 1")
    assert not result.success
    assert "oops" in result.stderr


def test_attachments_saved(tmp_path):
    """Attachments are written to ATTACHMENTS_DIR and accessible by the command."""
    att = Attachment(filename="data.txt", content=b"file content here", content_type="text/plain")
    parsed = _make_parsed(attachments=[att])
    # The command lists files in ATTACHMENTS_DIR and cats the attachment.
    result = execute_task(parsed, 'cat "$ATTACHMENTS_DIR/data.txt"')
    assert result.success
    assert "file content here" in result.stdout


def test_multiple_attachments():
    """Multiple attachments are all saved."""
    atts = [
        Attachment(filename="a.txt", content=b"aaa", content_type="text/plain"),
        Attachment(filename="b.txt", content=b"bbb", content_type="text/plain"),
    ]
    parsed = _make_parsed(attachments=atts)
    result = execute_task(parsed, 'ls "$ATTACHMENTS_DIR" | sort')
    assert result.success
    assert "a.txt" in result.stdout
    assert "b.txt" in result.stdout


def test_timeout(monkeypatch):
    """Command that exceeds timeout returns error."""
    import im_bot_email.executor as executor_mod

    monkeypatch.setattr(executor_mod, "TASK_TIMEOUT", 1)
    parsed = _make_parsed()
    result = execute_task(parsed, "sleep 10")
    assert not result.success
    assert result.return_code == -1
    assert "timed out" in result.stderr


def test_result_success_property():
    """TaskResult.success reflects return_code."""
    assert TaskResult(return_code=0, stdout="", stderr="").success
    assert not TaskResult(return_code=1, stdout="", stderr="").success
