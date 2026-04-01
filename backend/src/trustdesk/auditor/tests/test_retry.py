"""Tests for retry queue management."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.auditor.constants import (
    RETRY_BASE_DELAY_SECONDS,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY_SECONDS,
)
from trustdesk.auditor.retry import RetryManager


class TestRetryManager:
    """Retry queue: exponential backoff for failed on-chain writes."""

    def setup_method(self) -> None:
        self.queue: list[dict] = []
        self.manager = RetryManager(queue=self.queue)

    def test_enqueue_adds_task(self) -> None:
        self.manager.enqueue(
            task_id="tx_001",
            payload={"type": "reputation", "data": "test"},
        )
        assert len(self.queue) == 1
        assert self.queue[0]["task_id"] == "tx_001"

    def test_enqueue_sets_attempt_to_zero(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "test"})
        assert self.queue[0]["attempt"] == 0

    def test_compute_backoff_exponential(self) -> None:
        delay = self.manager.compute_backoff(attempt=0)
        assert delay == RETRY_BASE_DELAY_SECONDS  # 30s
        delay = self.manager.compute_backoff(attempt=1)
        assert delay == RETRY_BASE_DELAY_SECONDS * 2  # 60s
        delay = self.manager.compute_backoff(attempt=2)
        assert delay == RETRY_BASE_DELAY_SECONDS * 4  # 120s

    def test_compute_backoff_capped(self) -> None:
        delay = self.manager.compute_backoff(attempt=20)
        assert delay == RETRY_MAX_DELAY_SECONDS

    def test_get_due_tasks_returns_ready_items(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        # Set next_retry_at to the past
        self.queue[0]["next_retry_at"] = time.monotonic() - 10
        due = self.manager.get_due_tasks()
        assert len(due) == 1

    def test_get_due_tasks_skips_future_items(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        self.queue[0]["next_retry_at"] = time.monotonic() + 9999
        due = self.manager.get_due_tasks()
        assert len(due) == 0

    def test_mark_success_removes_task(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        self.manager.mark_success("tx_001")
        assert len(self.queue) == 0

    def test_mark_failure_increments_attempt(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        self.manager.mark_failure("tx_001")
        assert self.queue[0]["attempt"] == 1
        assert self.queue[0]["next_retry_at"] > time.monotonic()

    def test_mark_failure_removes_after_max_attempts(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        self.queue[0]["attempt"] = RETRY_MAX_ATTEMPTS - 1
        removed = self.manager.mark_failure("tx_001")
        assert removed is True
        assert len(self.queue) == 0

    def test_queue_length(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        self.manager.enqueue(task_id="tx_002", payload={"data": "b"})
        assert self.manager.queue_length == 2

    def test_mark_failure_unknown_task_id_returns_false(self) -> None:
        removed = self.manager.mark_failure("nonexistent_task")
        assert removed is False

    def test_mark_failure_mismatched_task_id_returns_false(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        removed = self.manager.mark_failure("nonexistent_task")
        assert removed is False
        assert self.manager.queue_length == 1

    def test_mark_success_unknown_task_id_is_noop(self) -> None:
        self.manager.enqueue(task_id="tx_001", payload={"data": "a"})
        self.manager.mark_success("nonexistent_task")
        assert self.manager.queue_length == 1
