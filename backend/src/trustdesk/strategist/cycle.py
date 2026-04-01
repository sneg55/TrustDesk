"""Cycle frequency management for the Strategist."""

from __future__ import annotations

import time
from collections.abc import Callable

from trustdesk.strategist.constants import CYCLE_INTERVALS, DEFAULT_CYCLE_INTERVAL


def get_cycle_interval(regime: str) -> int:
    """Return the cycle interval in seconds for the given regime."""
    return CYCLE_INTERVALS.get(regime, DEFAULT_CYCLE_INTERVAL)


class CycleTimer:
    """Tracks whether enough time has elapsed for the next strategist cycle."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._last_run: float | None = None

    def should_run(self, regime: str) -> bool:
        """Return True if the cycle interval has elapsed since last run."""
        if self._last_run is None:
            return True
        interval = get_cycle_interval(regime)
        return (self._clock() - self._last_run) >= interval

    def mark_run(self) -> None:
        """Record that a cycle just ran."""
        self._last_run = self._clock()

    def reset(self) -> None:
        """Reset the timer so next should_run returns True."""
        self._last_run = None
