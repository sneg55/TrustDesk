"""Position lifecycle management: monitoring, exits, and callbacks."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from trustdesk.orchestrator.constants import MAX_POSITION_DURATION_SECONDS

logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Why a position was closed."""

    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    INVALIDATION = "invalidation"
    MANUAL = "manual"


@dataclass
class PositionState:
    """Tracks an open position's lifecycle."""

    order_id: str
    pair: str
    side: str
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float | None = None
    opened_at: float = field(default_factory=time.time)
    closed: bool = False
    exit_reason: ExitReason | None = None


class PositionMonitor:
    """Monitors open positions for exit conditions."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._positions: dict[str, PositionState] = {}

    def track(self, position: PositionState) -> None:
        """Start tracking a position."""
        self._positions[position.order_id] = position

    def get(self, order_id: str) -> PositionState | None:
        """Get a tracked position by order_id."""
        return self._positions.get(order_id)

    def check_exit(
        self, order_id: str, current_price: float
    ) -> ExitReason | None:
        """Check if a position should be exited. Returns reason or None."""
        pos = self._positions.get(order_id)
        if pos is None or pos.closed:
            return None

        # Time-based exit
        elapsed = self._clock() - pos.opened_at
        if elapsed >= MAX_POSITION_DURATION_SECONDS:
            return ExitReason.TIME_EXIT

        # Stop loss
        if pos.side == "buy" and current_price <= pos.stop_loss:
            return ExitReason.STOP_LOSS
        if pos.side == "sell" and current_price >= pos.stop_loss:
            return ExitReason.STOP_LOSS

        # Take profit 2 (checked first for full exit)
        if pos.tp2 is not None:
            if pos.side == "buy" and current_price >= pos.tp2:
                return ExitReason.TP2_HIT
            if pos.side == "sell" and current_price <= pos.tp2:
                return ExitReason.TP2_HIT

        # Take profit 1
        if pos.side == "buy" and current_price >= pos.tp1:
            return ExitReason.TP1_HIT
        if pos.side == "sell" and current_price <= pos.tp1:
            return ExitReason.TP1_HIT

        return None

    def close(self, order_id: str, reason: ExitReason) -> PositionState | None:
        """Mark a position as closed."""
        pos = self._positions.get(order_id)
        if pos is None:
            return None
        pos.closed = True
        pos.exit_reason = reason
        return pos

    @property
    def open_positions(self) -> list[PositionState]:
        """Return all open (not closed) positions."""
        return [p for p in self._positions.values() if not p.closed]
