"""Tests for sender whitelist filtering."""

from email.mime.text import MIMEText
from unittest.mock import patch, MagicMock

from im_bot_email.__main__ import main


def _make_raw_email(sender="alice@example.com", subject="Test", body="Hello"):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "bot@example.com"
    return msg


def _run_with_config(cfg, raw_msg):
    """Run on_message callback with given config and capture execute_task calls."""
    with patch("im_bot_email.__main__.get_config", return_value=cfg), \
         patch("im_bot_email.__main__.idle_loop") as mock_idle, \
         patch("im_bot_email.__main__.execute_task") as mock_exec, \
         patch("im_bot_email.__main__.send_reply"):
        mock_exec.return_value = MagicMock(success=True, stdout="ok", stderr="")
        main()
        # Extract the on_message callback and call it
        callback = mock_idle.call_args[1].get("callback") or mock_idle.call_args[0][4]
        callback(raw_msg)
        return mock_exec


def _base_cfg(**overrides):
    cfg = {
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 465,
        "email_user": "bot@gmail.com",
        "email_password": "pass",
        "task_command": "echo",
        "log_level": "INFO",
        "allowed_senders": set(),
    }
    cfg.update(overrides)
    return cfg


def test_no_whitelist_allows_all():
    mock_exec = _run_with_config(
        _base_cfg(allowed_senders=set()),
        _make_raw_email(sender="anyone@example.com"),
    )
    mock_exec.assert_called_once()


def test_whitelist_allows_listed_sender():
    mock_exec = _run_with_config(
        _base_cfg(allowed_senders={"alice@example.com"}),
        _make_raw_email(sender="alice@example.com"),
    )
    mock_exec.assert_called_once()


def test_whitelist_blocks_unlisted_sender():
    mock_exec = _run_with_config(
        _base_cfg(allowed_senders={"alice@example.com"}),
        _make_raw_email(sender="spammer@evil.com"),
    )
    mock_exec.assert_not_called()


def test_whitelist_case_insensitive():
    mock_exec = _run_with_config(
        _base_cfg(allowed_senders={"alice@example.com"}),
        _make_raw_email(sender="Alice@Example.COM"),
    )
    mock_exec.assert_called_once()


def test_whitelist_handles_display_name():
    mock_exec = _run_with_config(
        _base_cfg(allowed_senders={"alice@example.com"}),
        _make_raw_email(sender="Alice Smith <alice@example.com>"),
    )
    mock_exec.assert_called_once()


def test_whitelist_multiple_senders():
    allowed = {"alice@example.com", "bob@example.com"}
    mock_exec = _run_with_config(
        _base_cfg(allowed_senders=allowed),
        _make_raw_email(sender="bob@example.com"),
    )
    mock_exec.assert_called_once()

    mock_exec = _run_with_config(
        _base_cfg(allowed_senders=allowed),
        _make_raw_email(sender="charlie@example.com"),
    )
    mock_exec.assert_not_called()
