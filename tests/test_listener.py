"""Tests for IMAP IDLE listener."""

import email
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

from im_bot_email.listener import connect, fetch_new_messages, _search_unseen


def _make_raw_email(subject="Test", body="Hello"):
    """Create a raw RFC-822 email bytes for testing."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "alice@example.com"
    msg["To"] = "bot@example.com"
    return msg.as_bytes()


@patch("im_bot_email.listener.IMAPClient")
def test_connect(MockClient):
    client = MockClient.return_value
    result = connect("imap.example.com", 993, "user", "pass")

    MockClient.assert_called_once_with("imap.example.com", port=993, ssl=True)
    client.login.assert_called_once_with("user", "pass")
    client.select_folder.assert_called_once_with("INBOX")
    assert result is client


@patch("im_bot_email.listener.IMAPClient")
def test_fetch_new_messages(MockClient):
    client = MockClient.return_value
    raw = _make_raw_email("Hello World", "body text")
    client.fetch.return_value = {1: {b"RFC822": raw}}

    messages = fetch_new_messages(client, [1])

    assert len(messages) == 1
    assert messages[0]["Subject"] == "Hello World"


def test_fetch_new_messages_empty():
    """No UIDs → no fetch call, empty list."""
    client = MagicMock()
    assert fetch_new_messages(client, []) == []
    client.fetch.assert_not_called()


@patch("im_bot_email.listener.IMAPClient")
def test_search_unseen(MockClient):
    client = MockClient.return_value
    client.search.return_value = [5, 6]
    assert _search_unseen(client) == [5, 6]
    client.search.assert_called_once_with(["UNSEEN"])
