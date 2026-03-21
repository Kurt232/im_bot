"""Configuration from environment variables."""

import os


def get_config() -> dict:
    """Read configuration from environment variables."""
    auth_method = os.environ.get("AUTH_METHOD", "password")

    cfg = {
        "imap_host": os.environ["IMAP_HOST"],
        "imap_port": int(os.environ.get("IMAP_PORT", "993")),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "465")),
        "email_user": os.environ["EMAIL_USER"],
        "task_command": os.environ.get("TASK_COMMAND", "echo"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "auth_method": auth_method,
    }

    if auth_method == "oauth2":
        cfg["oauth2_client_id"] = os.environ["OAUTH2_CLIENT_ID"]
        cfg["oauth2_tenant_id"] = os.environ.get("OAUTH2_TENANT_ID", "common")
        cfg["oauth2_token_cache"] = os.environ.get("OAUTH2_TOKEN_CACHE", ".token_cache.json")
        # password not required for oauth2
        cfg["email_password"] = ""
    else:
        cfg["email_password"] = os.environ["EMAIL_PASSWORD"]

    return cfg
