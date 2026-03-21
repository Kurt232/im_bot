"""Entry point — wire listener, parser, executor, and replier together."""

import logging

from .config import get_config
from .executor import execute_task
from .listener import idle_loop
from .parser import parse_email
from .replier import send_reply


def main() -> None:
    cfg = get_config()
    logging.basicConfig(
        level=cfg["log_level"],
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    def on_message(raw_msg):
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

    idle_loop(
        host=cfg["imap_host"],
        port=cfg["imap_port"],
        user=cfg["email_user"],
        password=cfg["email_password"],
        callback=on_message,
    )


if __name__ == "__main__":
    main()
