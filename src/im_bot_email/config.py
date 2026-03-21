"""Configuration from environment variables."""

import os


def get_config() -> dict:
    """Read configuration from environment variables."""
    # Comma-separated list of allowed sender addresses (empty = allow all).
    raw_allowed = os.environ.get("ALLOWED_SENDERS", "")
    allowed = {addr.strip().lower() for addr in raw_allowed.split(",") if addr.strip()}

    return {
        "imap_host": os.environ["IMAP_HOST"],
        "imap_port": int(os.environ.get("IMAP_PORT", "993")),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "465")),
        "email_user": os.environ["EMAIL_USER"],
        "email_password": os.environ["EMAIL_PASSWORD"],
        "task_command": os.environ.get("TASK_COMMAND", "echo"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "allowed_senders": allowed,
    }
