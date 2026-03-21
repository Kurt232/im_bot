"""IMAP IDLE listener — connects to mailbox and yields new messages in real time."""

import email
import logging
import time
from email.message import Message

from imapclient import IMAPClient

logger = logging.getLogger(__name__)

# RFC 2177: renew IDLE before server drops the connection (typically 30 min).
# We renew every 5 minutes to be safe.
IDLE_RENEW_SECONDS = 5 * 60

# How long each idle_check waits for server responses.
IDLE_CHECK_TIMEOUT = 30


def connect(host: str, port: int, user: str, password: str) -> IMAPClient:
    """Create an authenticated IMAP connection and select INBOX."""
    client = IMAPClient(host, port=port, ssl=True)
    client.login(user, password)
    client.select_folder("INBOX")
    logger.info("Connected to %s as %s", host, user)
    return client


def fetch_new_messages(client: IMAPClient, uids: list[int]) -> list[Message]:
    """Fetch and parse RFC-822 messages for the given UIDs."""
    if not uids:
        return []
    raw = client.fetch(uids, ["RFC822"])
    messages: list[Message] = []
    for uid, data in raw.items():
        msg = email.message_from_bytes(data[b"RFC822"])
        logger.info("Fetched UID %s: %s", uid, msg.get("Subject", "(no subject)"))
        messages.append(msg)
    return messages


def _search_unseen(client: IMAPClient) -> list[int]:
    """Return UIDs of unseen messages."""
    return client.search(["UNSEEN"])


def idle_loop(
    host: str,
    port: int,
    user: str,
    password: str,
    callback,
) -> None:
    """Run the IMAP IDLE loop, calling *callback(message)* for each new email.

    Reconnects automatically on connection errors.
    """
    while True:
        try:
            _idle_session(host, port, user, password, callback)
        except Exception:
            logger.exception("IMAP connection lost, reconnecting in 10 s")
            time.sleep(10)


def _idle_session(
    host: str,
    port: int,
    user: str,
    password: str,
    callback,
) -> None:
    """A single IMAP session: connect, process unseen mail, then IDLE."""
    client = connect(host, port, user, password)
    try:
        # Process any mail that arrived while we were offline.
        for msg in fetch_new_messages(client, _search_unseen(client)):
            callback(msg)

        # Enter IDLE loop.
        while True:
            client.idle()
            idle_start = time.monotonic()

            while time.monotonic() - idle_start < IDLE_RENEW_SECONDS:
                responses = client.idle_check(timeout=IDLE_CHECK_TIMEOUT)
                if any(resp for resp in responses if resp[1] == b"EXISTS"):
                    client.idle_done()
                    for msg in fetch_new_messages(client, _search_unseen(client)):
                        callback(msg)
                    break
            else:
                # Renew IDLE — no new mail, just restart.
                client.idle_done()
                logger.debug("IDLE renewed")
    finally:
        try:
            client.logout()
        except Exception:
            pass
