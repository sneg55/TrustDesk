# backend/src/trustdesk/risk_manager/circuit_breaker.py
"""Circuit breaker for LLM availability."""
from __future__ import annotations

import time
from enum import StrEnum


class CircuitState(StrEnum):
    """State of the circuit breaker."""

    CLOSED = "CLOSED"  # Normal operation, LLM available
    OPEN = "OPEN"  # LLM unavailable, skip soft checks
    HALF_OPEN = "HALF_OPEN"  # Testing if LLM is back


class CircuitBreaker:
    """Tracks LLM availability and skips soft checks when unavailable.

    - CLOSED: LLM is available, all checks run.
    - OPEN: LLM has failed repeatedly, skip soft checks.
    - HALF_OPEN: After timeout, allow one attempt to test LLM.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_s: int = 60,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._reset_timeout_s = reset_timeout_s
        self._failure_count = 0
        self._opened_at: float | None = None
        self._probe_failed: bool = False
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        """Current state, accounting for timeout transitions."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            # If a probe just failed, stay OPEN until explicitly reset
            if self._probe_failed:
                return CircuitState.OPEN
            elapsed = time.monotonic() - self._opened_at
            if elapsed > self._reset_timeout_s:
                return CircuitState.HALF_OPEN
        return self._state

    @property
    def is_available(self) -> bool:
        """Whether soft checks should run."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful LLM call."""
        self._failure_count = 0
        self._opened_at = None
        self._probe_failed = False
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed LLM call."""
        current = self.state
        if current == CircuitState.HALF_OPEN:
            # Failed during probe -- reopen with fresh timestamp
            self._probe_failed = True
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            return

        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._probe_failed = False
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
