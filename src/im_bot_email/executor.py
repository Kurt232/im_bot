"""Task executor — run TASK_COMMAND with parsed email as input."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass

from .parser import ParsedEmail

logger = logging.getLogger(__name__)

# Default timeout for task execution (seconds).
TASK_TIMEOUT = int(os.environ.get("TASK_TIMEOUT", "300"))


@dataclass
class TaskResult:
    """Result of running TASK_COMMAND."""

    return_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.return_code == 0


def execute_task(parsed: ParsedEmail, task_command: str) -> TaskResult:
    """Run *task_command* with the email task description on stdin.

    Attachments are saved to a temporary directory whose path is passed
    via the ``ATTACHMENTS_DIR`` environment variable so the command can
    access them.
    """
    task_text = parsed.to_task_description()

    with tempfile.TemporaryDirectory(prefix="im_bot_") as tmpdir:
        # Save attachments so the command can read them.
        for att in parsed.attachments:
            path = os.path.join(tmpdir, att.filename)
            with open(path, "wb") as f:
                f.write(att.content)
            logger.debug("Saved attachment %s to %s", att.filename, path)

        env = {**os.environ, "ATTACHMENTS_DIR": tmpdir}

        logger.info(
            "Executing task_command=%r (timeout=%ds, attachments=%d)",
            task_command,
            TASK_TIMEOUT,
            len(parsed.attachments),
        )

        try:
            proc = subprocess.run(
                task_command,
                shell=True,
                input=task_text,
                capture_output=True,
                text=True,
                timeout=TASK_TIMEOUT,
                env=env,
            )
            result = TaskResult(
                return_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            logger.error("Task command timed out after %d seconds", TASK_TIMEOUT)
            result = TaskResult(
                return_code=-1,
                stdout="",
                stderr=f"Task timed out after {TASK_TIMEOUT} seconds",
            )

    if result.success:
        logger.info("Task completed successfully (stdout %d bytes)", len(result.stdout))
    else:
        logger.warning(
            "Task failed (rc=%d, stderr=%s)", result.return_code, result.stderr[:200]
        )

    return result
