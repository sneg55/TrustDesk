# backend/src/trustdesk/reputation/tiers.py
"""Tier definitions and limits mapping."""
from __future__ import annotations

from enum import IntEnum

from trustdesk.reputation.types import TierLimits


class TierName(IntEnum):
    """Reputation tiers, ordered by trust level."""

    UNPROVEN = 0
    ESTABLISHED = 1
    TRUSTED = 2


TIER_DEFINITIONS: dict[TierName, TierLimits] = {
    TierName.UNPROVEN: TierLimits(
        capital_usd=100,
        max_position_pct=3.0,
        max_trades=1,
        max_daily_loss_pct=3.0,
    ),
    TierName.ESTABLISHED: TierLimits(
        capital_usd=500,
        max_position_pct=7.0,
        max_trades=3,
        max_daily_loss_pct=5.0,
    ),
    TierName.TRUSTED: TierLimits(
        capital_usd=1000,
        max_position_pct=10.0,
        max_trades=5,
        max_daily_loss_pct=5.0,
    ),
}


def get_tier_limits(tier: TierName) -> TierLimits:
    """Return a copy of the limits for the given tier."""
    src = TIER_DEFINITIONS[tier]
    return TierLimits(
        capital_usd=src.capital_usd,
        max_position_pct=src.max_position_pct,
        max_trades=src.max_trades,
        max_daily_loss_pct=src.max_daily_loss_pct,
    )
