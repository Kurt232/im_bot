"""Entry point — wire listener, parser, executor, and replier together."""

import logging
from concurrent.futures import ThreadPoolExecutor

from email.utils import parseaddr

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

    allowed = cfg["allowed_senders"]
    pool = ThreadPoolExecutor(max_workers=4)

    def _process_message(raw_msg):
        try:
            parsed = parse_email(raw_msg)
            if allowed:
                _, addr = parseaddr(parsed.sender)
                if addr.lower() not in allowed:
                    logger.info("Ignoring mail from non-whitelisted sender: %s", parsed.sender)
                    return
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

    def on_message(raw_msg):
        pool.submit(_process_message, raw_msg)

    idle_loop(
        host=cfg["imap_host"],
        port=cfg["imap_port"],
        user=cfg["email_user"],
        password=cfg["email_password"],
        callback=on_message,
    )


if __name__ == "__main__":
    main()
