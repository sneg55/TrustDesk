"""SignalPayload — output of the Signal Engine, input to the Strategist."""
from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel


class Alignment(enum.Enum):
    """Signal alignment grade."""

    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NO_SIGNAL = "NO_SIGNAL"


class AlignmentBreakdown(BaseModel):
    ema_crossover: bool
    adx_trending: bool
    volume_confirmed: bool
    obv_aligned: bool
    book_imbalance_aligned: bool


class DerivedValues(BaseModel):
    suggested_stop_distance: float
    position_size_pct: float
    regime_aligned: bool


class SignalPayload(BaseModel):
    pair: str
    price: float
    regime: str
    alignment: Alignment
    alignment_score: float
    breakdown: AlignmentBreakdown
    derived: DerivedValues
    indicators: dict[str, Any]
