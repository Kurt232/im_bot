"""Configuration from environment variables and senders.yaml."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_USERS_PATH = "users.yaml"


def _load_users(path: str) -> dict[str, dict]:
    """Load allowed users from a YAML file.

    Returns a dict of ``{email: {"max_workers": int}}``.
    Falls back to env var ``ALLOWED_SENDERS`` for backwards compatibility.
    """
    p = Path(path)
    if p.is_file():
        with open(p) as f:
            data = yaml.safe_load(f) or {}
        users: dict[str, dict] = {}
        for email, cfg in (data.get("users") or {}).items():
            cfg = cfg or {}
            users[email.strip().lower()] = {
                "max_workers": int(cfg.get("max_workers", 1)),
            }
        logger.info("Loaded %d users from %s", len(users), path)
        return users

    # Fallback: ALLOWED_SENDERS env var (comma-separated emails, all get max_workers=1).
    raw = os.environ.get("ALLOWED_SENDERS", "")
    if raw.strip():
        users = {
            addr.strip().lower(): {"max_workers": 1}
            for addr in raw.split(",")
            if addr.strip()
        }
        logger.info("Loaded %d users from ALLOWED_SENDERS env var", len(users))
        return users

    logger.warning("No users config found — all senders allowed")
    return {}


def get_config() -> dict:
    """Read configuration from environment variables and senders.yaml."""
    users_path = os.environ.get("USERS_CONFIG", _DEFAULT_USERS_PATH)
    user_config = _load_users(users_path)

    return {
        "imap_host": os.environ["IMAP_HOST"],
        "imap_port": int(os.environ.get("IMAP_PORT", "993")),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "465")),
        "email_user": os.environ["EMAIL_USER"],
        "email_password": os.environ["EMAIL_PASSWORD"],
        "task_command": os.environ.get("TASK_COMMAND", "echo"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "queue_size": int(os.environ.get("QUEUE_SIZE", "2")),
        "user_config": user_config,
    }
