# backend/src/trustdesk/reputation/types.py
"""Internal types for the reputation engine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class FeedbackKind(IntEnum):
    """Kind of on-chain feedback event."""

    TRADE_OPEN = 1
    TRADE_CLOSE = 2
    TIER_CHANGE = 3


@dataclass(frozen=True, slots=True)
class TierLimits:
    """Capital and risk limits for a tier."""

    capital_usd: int
    max_position_pct: float
    max_trades: int
    max_daily_loss_pct: float


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    """A single on-chain feedback entry."""

    kind: FeedbackKind
    score: int
    pnl_usd: float
    timestamp: int
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class PromotionResult:
    """Result of a promotion/demotion check."""

    changed: bool
    old_tier: str
    new_tier: str
    reason: str
