"""Pydantic response models for the Strykr/PRISM API."""
from __future__ import annotations

from pydantic import BaseModel


class ResolvedAsset(BaseModel):
    """Canonical asset identity returned by /resolve/{asset}."""

    symbol: str
    name: str
    type: str
    confidence: float
    venues: list[dict]


class Indicators(BaseModel):
    """Technical indicator values embedded in a PrismSignal."""

    rsi: float | None = None
    macd: float | None = None
    macd_histogram: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None


class PrismSignal(BaseModel):
    """AI-powered market signal returned by /signals/{symbol}."""

    symbol: str
    overall_signal: str
    direction: str
    strength: str
    bullish_score: int
    bearish_score: int
    net_score: int
    current_price: float
    indicators: Indicators
    active_signals: list[dict]


class PrismRisk(BaseModel):
    """Risk metrics returned by /risk/{symbol}."""

    symbol: str
    daily_volatility: float
    annual_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    current_drawdown: float
