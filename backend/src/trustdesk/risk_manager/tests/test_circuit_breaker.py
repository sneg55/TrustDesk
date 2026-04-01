# backend/src/trustdesk/risk_manager/tests/test_circuit_breaker.py
"""Tests for circuit breaker -- LLM unavailable mode."""

from trustdesk.risk_manager.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_initially_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_is_available_when_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        assert cb.is_available is True

    def test_is_unavailable_when_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_available is False

    def test_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=0)
        for _ in range(3):
            cb.record_failure()
        # reset_timeout_s=0 so it should immediately be half-open
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
