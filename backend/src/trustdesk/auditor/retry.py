"""Retry queue management for failed on-chain writes.

Uses in-memory list for unit tests; production code writes to the
RetryQueue SQLAlchemy model via the same interface.
"""

from __future__ import annotations

import time
from typing import Any

from trustdesk.auditor.constants import (
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY_SECONDS,
)


class RetryManager:
    """Manages retry queue with exponential backoff."""

    def __init__(self, queue: list[dict[str, Any]] | None = None) -> None:
        self._queue: list[dict[str, Any]] = queue if queue is not None else []

    @property
    def queue_length(self) -> int:
        """Return number of tasks in the queue."""
        return len(self._queue)

    def enqueue(self, *, task_id: str, payload: dict[str, Any]) -> None:
        """Add a failed task to the retry queue."""
        self._queue.append(
            {
                "task_id": task_id,
                "payload": payload,
                "attempt": 0,
                "next_retry_at": time.monotonic(),
            },
        )

    def compute_backoff(self, attempt: int) -> float:
        """Compute delay in seconds using exponential backoff.

        delay = min(max_delay, base_delay * 2^attempt)
        """
        delay = RETRY_BASE_DELAY_SECONDS * (2**attempt)
        return min(delay, RETRY_MAX_DELAY_SECONDS)

    def get_due_tasks(self) -> list[dict[str, Any]]:
        """Return tasks whose next_retry_at is in the past."""
        now = time.monotonic()
        return [t for t in self._queue if t["next_retry_at"] <= now]

    def mark_success(self, task_id: str) -> None:
        """Remove a successfully completed task."""
        self._queue[:] = [t for t in self._queue if t["task_id"] != task_id]

    def mark_failure(self, task_id: str) -> bool:
        """Increment attempt counter and schedule next retry.

        Returns True if the task was removed (max attempts exceeded).
        """
        for i, task in enumerate(self._queue):
            if task["task_id"] == task_id:
                task["attempt"] += 1
                if task["attempt"] >= RETRY_MAX_ATTEMPTS:
                    self._queue.pop(i)
                    return True
                task["next_retry_at"] = (
                    time.monotonic() + self.compute_backoff(task["attempt"])
                )
                return False
        return False
