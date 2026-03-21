"""Entry point — wire listener, parser, executor, queue, and replier together."""

import logging
import os
import threading

from email.utils import parseaddr

from .config import get_config
from .executor import execute_task
from .listener import idle_loop
from .parser import parse_email
from .queue_manager import QueueManager
from .replier import send_reply, send_status_reply

logger = logging.getLogger(__name__)


def main() -> None:
    cfg = get_config()
    logging.basicConfig(
        level=cfg["log_level"],
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    user_cfg = cfg["user_config"]
    allowed = set(user_cfg.keys()) if user_cfg else set()
    user_limits = {email: s["max_workers"] for email, s in user_cfg.items()}

    queue = QueueManager(
        max_workers=cfg["queue_size"],
        sender_limits=user_limits,
    )

    smtp_kw = dict(
        smtp_host=cfg["smtp_host"],
        smtp_port=cfg["smtp_port"],
        email_user=cfg["email_user"],
        email_password=cfg["email_password"],
    )

    def on_message(raw_msg):
        try:
            parsed = parse_email(raw_msg)
            _, addr = parseaddr(parsed.sender)
            addr_lower = addr.lower() if addr else ""

            if allowed and addr_lower not in allowed:
                logger.info("Ignoring mail from non-whitelisted sender: %s", parsed.sender)
                return

            def do_task():
                result = execute_task(parsed, cfg["task_command"])
                send_reply(parsed, result, **smtp_kw)

            status, position = queue.submit(addr_lower, do_task)

            # Send immediate status reply (in background to not block IDLE loop).
            timeout_min = int(os.environ.get("TIMEOUT", 300)) // 60
            if status == "executing":
                body = f"正在执行您的任务，预计最长 {timeout_min} 分钟，请稍候..."
            else:
                body = f"队列已满，您排在第 {position} 位，请耐心等待。（每个任务最长 {timeout_min} 分钟）"

            threading.Thread(
                target=send_status_reply,
                args=(parsed, body),
                kwargs=smtp_kw,
                daemon=True,
            ).start()

        except Exception:
            logger.exception("Failed to process message")

    idle_loop(
        host=cfg["imap_host"],
        port=cfg["imap_port"],
        user=cfg["email_user"],
        password=cfg["email_password"],
        callback=on_message,
    )


if __name__ == "__main__":
    main()
