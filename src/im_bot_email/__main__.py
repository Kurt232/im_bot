"""Entry point — wire listener, parser, executor, and replier together."""

import logging

from .config import get_config
from .executor import execute_task
from .listener import idle_loop
from .parser import parse_email
from .replier import send_reply

logger = logging.getLogger(__name__)


def main() -> None:
    cfg = get_config()
    logging.basicConfig(
        level=cfg["log_level"],
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    oauth2_mgr = None
    if cfg["auth_method"] == "oauth2":
        from .oauth2 import OAuth2Manager

        oauth2_mgr = OAuth2Manager(
            client_id=cfg["oauth2_client_id"],
            tenant_id=cfg["oauth2_tenant_id"],
            token_cache_path=cfg["oauth2_token_cache"],
        )
        # Eagerly acquire token so device-code prompt happens at startup.
        oauth2_mgr.get_access_token()

    def on_message(raw_msg):
        try:
            parsed = parse_email(raw_msg)
            result = execute_task(parsed, cfg["task_command"])
            send_reply(
                parsed,
                result,
                smtp_host=cfg["smtp_host"],
                smtp_port=cfg["smtp_port"],
                email_user=cfg["email_user"],
                email_password=cfg["email_password"],
            )
        except Exception:
            logger.exception("Failed to process message")

    idle_loop(
        host=cfg["imap_host"],
        port=cfg["imap_port"],
        user=cfg["email_user"],
        password=cfg["email_password"],
        callback=on_message,
        oauth2_manager=oauth2_mgr,
    )


if __name__ == "__main__":
    main()
