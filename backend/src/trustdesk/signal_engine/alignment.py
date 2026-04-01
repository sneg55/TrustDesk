"""Signal alignment scoring and derived value computation.

Pure functions that compute alignment from indicator outputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from trustdesk.schemas.signal_payload import (
    Alignment,
    AlignmentBreakdown,
    DerivedValues,
)
from trustdesk.signal_engine.constants import (
    ADX_RANGING_THRESHOLD,
    ADX_TRENDING_THRESHOLD,
    BOOK_IMBALANCE_THRESHOLD,
    POSITION_SIZE_MODERATE,
    POSITION_SIZE_NONE,
    POSITION_SIZE_STRONG,
    POSITION_SIZE_WEAK,
    STOP_ATR_MULTIPLIER,
    VOLUME_THRESHOLD,
)
from trustdesk.signal_engine.regime import Regime
from trustdesk.signal_engine.types import CrossoverState, OBVTrend

_TOTAL_SIGNALS = 5


@dataclass(frozen=True)
class AlignmentResult:
    """Result of alignment computation."""

    score: float
    grade: Alignment
    breakdown: AlignmentBreakdown


def compute_alignment(
    *,
    crossover: CrossoverState,
    adx: float,
    volume_multiplier: float,
    obv_trend: OBVTrend,
    book_imbalance: float,
) -> AlignmentResult:
    """Compute alignment score from directional signals.

    Counts how many of 5 key signals agree on a long bias.
    """
    ema_ok = crossover == CrossoverState.BULLISH
    adx_ok = adx > ADX_TRENDING_THRESHOLD or adx < ADX_RANGING_THRESHOLD
    vol_ok = volume_multiplier > VOLUME_THRESHOLD
    obv_ok = obv_trend == OBVTrend.RISING
    book_ok = book_imbalance > BOOK_IMBALANCE_THRESHOLD

    count = sum([ema_ok, adx_ok, vol_ok, obv_ok, book_ok])
    score = count / _TOTAL_SIGNALS

    if score >= 1.0:
        grade = Alignment.STRONG
    elif score >= 0.8:
        grade = Alignment.MODERATE
    elif score >= 0.6:
        grade = Alignment.WEAK
    else:
        grade = Alignment.NO_SIGNAL

    breakdown = AlignmentBreakdown(
        ema_crossover=ema_ok,
        adx_trending=adx_ok,
        volume_confirmed=vol_ok,
        obv_aligned=obv_ok,
        book_imbalance_aligned=book_ok,
    )
    return AlignmentResult(
        score=score, grade=grade, breakdown=breakdown
    )


def compute_stop_distance(atr: float) -> float:
    """Suggested stop distance = 1.5 * ATR."""
    return STOP_ATR_MULTIPLIER * atr


def compute_position_size(grade: Alignment) -> float:
    """Position size percentage from alignment grade."""
    return {
        Alignment.STRONG: POSITION_SIZE_STRONG,
        Alignment.MODERATE: POSITION_SIZE_MODERATE,
        Alignment.WEAK: POSITION_SIZE_WEAK,
        Alignment.NO_SIGNAL: POSITION_SIZE_NONE,
    }[grade]


def compute_derived_values(
    *,
    atr: float,
    grade: Alignment,
    regime: Regime,
) -> DerivedValues:
    """Compute derived trading values."""
    regime_aligned = regime in (
        Regime.TRENDING_UP,
        Regime.TRENDING_DOWN,
    )
    return DerivedValues(
        suggested_stop_distance=compute_stop_distance(atr),
        position_size_pct=compute_position_size(grade),
        regime_aligned=regime_aligned,
    )
