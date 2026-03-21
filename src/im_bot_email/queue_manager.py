"""Task queue manager with per-sender concurrency control."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class _QueuedTask:
    sender: str
    run: Callable[[], None]


class QueueManager:
    """Manages task execution with global and per-sender concurrency limits.

    Parameters
    ----------
    max_workers:
        Maximum number of tasks executing concurrently (QUEUE_SIZE).
    sender_limits:
        Per-sender max concurrent tasks, e.g. ``{"user@x.com": 1}``.
        Senders not in the dict default to 1.
    """

    def __init__(self, max_workers: int, sender_limits: dict[str, int]) -> None:
        self._lock = threading.Lock()
        self._max_workers = max_workers
        self._sender_limits = sender_limits
        self._active_count = 0
        self._sender_active: dict[str, int] = defaultdict(int)
        self._waiting: list[_QueuedTask] = []

    def submit(self, sender: str, task_fn: Callable[[], None]) -> tuple[str, int]:
        """Submit a task for *sender*.

        Returns ``("executing", 0)`` if the task starts immediately,
        or ``("queued", position)`` if it was queued (1-indexed).
        """
        with self._lock:
            sender_limit = self._sender_limits.get(sender, 1)

            if (
                self._active_count < self._max_workers
                and self._sender_active[sender] < sender_limit
            ):
                self._active_count += 1
                self._sender_active[sender] += 1
                threading.Thread(
                    target=self._run, args=(sender, task_fn), daemon=True
                ).start()
                return ("executing", 0)

            self._waiting.append(_QueuedTask(sender=sender, run=task_fn))
            position = len(self._waiting)
            logger.info(
                "Task queued for %s at position %d (%d active)",
                sender,
                position,
                self._active_count,
            )
            return ("queued", position)

    @property
    def pending_count(self) -> int:
        """Number of tasks waiting in the queue."""
        with self._lock:
            return len(self._waiting)

    def _run(self, sender: str, task_fn: Callable[[], None]) -> None:
        try:
            task_fn()
        except Exception:
            logger.exception("Task execution failed for %s", sender)
        finally:
            self._on_done(sender)

    def _on_done(self, sender: str) -> None:
        with self._lock:
            self._active_count -= 1
            self._sender_active[sender] -= 1
            self._dequeue()

    def _dequeue(self) -> None:
        """Start the next eligible waiting task. Must hold ``_lock``."""
        for i, task in enumerate(self._waiting):
            sender_limit = self._sender_limits.get(task.sender, 1)
            if (
                self._active_count < self._max_workers
                and self._sender_active[task.sender] < sender_limit
            ):
                self._waiting.pop(i)
                self._active_count += 1
                self._sender_active[task.sender] += 1
                threading.Thread(
                    target=self._run, args=(task.sender, task.run), daemon=True
                ).start()
                logger.info("Dequeued task for %s", task.sender)
                return
