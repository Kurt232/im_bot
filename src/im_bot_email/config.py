"""Configuration from environment variables."""

import os


def get_config() -> dict:
    """Read configuration from environment variables."""
    return {
        "imap_host": os.environ["IMAP_HOST"],
        "imap_port": int(os.environ.get("IMAP_PORT", "993")),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "465")),
        "email_user": os.environ["EMAIL_USER"],
        "email_password": os.environ["EMAIL_PASSWORD"],
        "task_command": os.environ.get("TASK_COMMAND", "echo"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
    }
