"""SignalPayload — output of the Signal Engine, input to the Strategist."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AlignmentBreakdown(BaseModel):
    ema_direction: bool
    adx_strength: bool
    volume_confirmation: bool
    obv_trend_match: bool
    book_imbalance_favorable: bool


class Alignment(BaseModel):
    score: float
    grade: Literal["STRONG", "MODERATE", "WEAK", "NO_SIGNAL"]
    signals_agreeing: int
    signals_total: int = 5
    breakdown: AlignmentBreakdown


class DerivedValues(BaseModel):
    suggested_stop_distance: float
    position_size_pct: float
    regime_aligned: bool


class SignalPayload(BaseModel):
    timestamp: datetime
    pair: str
    price: float
    regime: Literal["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"]
    regime_confidence: float
    regime_changed: bool
    signals: dict[str, Any]
    alignment: Alignment
    derived: DerivedValues
