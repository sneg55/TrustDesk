"""Regime detection for market state classification.

Pure function. Takes pre-computed indicator values and returns
a Regime classification.
"""

from __future__ import annotations

import enum

from trustdesk.signal_engine.constants import (
    ADX_RANGING_THRESHOLD,
    ADX_TRENDING_THRESHOLD,
    ATR_VOLATILE_MULTIPLIER,
)
from trustdesk.signal_engine.types import OBVTrend


class Regime(enum.Enum):
    """Market regime classification."""

    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"


def detect_regime(
    *,
    adx: float,
    ema_fast: float,
    ema_medium: float,
    ema_slow: float,
    obv_trend: OBVTrend,
    atr_current: float,
    atr_avg: float,
    bollinger_width_current: float,
    bollinger_width_prev: float,
) -> Regime:
    """Detect market regime from indicator values.

    Priority order: VOLATILE > TRENDING > RANGING (default).
    """
    # -- Volatile: ATR spike + Bollinger expanding rapidly --
    bb_expanding = bollinger_width_current > bollinger_width_prev * 1.5
    if atr_current > ATR_VOLATILE_MULTIPLIER * atr_avg and bb_expanding:
        return Regime.VOLATILE

    # -- Trending: ADX > 25, EMA alignment, OBV confirmation --
    if adx > ADX_TRENDING_THRESHOLD:
        if (
            ema_fast > ema_medium > ema_slow
            and obv_trend == OBVTrend.RISING
        ):
            return Regime.TRENDING_UP
        if (
            ema_fast < ema_medium < ema_slow
            and obv_trend == OBVTrend.FALLING
        ):
            return Regime.TRENDING_DOWN

    # -- Ranging: ADX < 20, Bollinger contracting, price between EMAs --
    bb_contracting = bollinger_width_current <= bollinger_width_prev
    ema_min = min(ema_medium, ema_slow)
    ema_max = max(ema_medium, ema_slow)
    price_between = ema_min <= ema_fast <= ema_max

    if adx < ADX_RANGING_THRESHOLD and (
        bb_contracting or price_between
    ):
        return Regime.RANGING

    # Default: RANGING
    return Regime.RANGING
