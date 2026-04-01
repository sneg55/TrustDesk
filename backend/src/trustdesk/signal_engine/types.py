"""Internal types for the signal engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import pandas as pd

OHLC_REQUIRED_COLS = frozenset(
    {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "count",
    }
)

TRADE_REQUIRED_COLS = frozenset({"price", "volume", "time", "side"})


class CrossoverState(enum.Enum):
    """EMA crossover direction."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class OBVTrend(enum.Enum):
    """On-Balance Volume trend direction."""

    RISING = "RISING"
    FALLING = "FALLING"
    FLAT = "FLAT"


@dataclass(frozen=True)
class OHLCData:
    """Validated OHLC candlestick data."""

    pair: str
    interval: int
    df: pd.DataFrame

    def __post_init__(self) -> None:
        missing = OHLC_REQUIRED_COLS - set(self.df.columns)
        if missing:
            msg = f"Missing required columns: {sorted(missing)}"
            raise ValueError(msg)


@dataclass(frozen=True)
class TickerData:
    """Current ticker snapshot."""

    pair: str
    ask: float
    bid: float
    last: float
    volume_today: float
    vwap_today: float

    @property
    def spread(self) -> float:
        """Absolute spread."""
        return self.ask - self.bid

    @property
    def spread_pct(self) -> float:
        """Spread as percentage of last price."""
        return (self.spread / self.last) * 100


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Order book snapshot with asks and bids."""

    pair: str
    asks: pd.DataFrame
    bids: pd.DataFrame


@dataclass(frozen=True)
class TradeFlowData:
    """Recent trade data for flow analysis."""

    pair: str
    df: pd.DataFrame

    def __post_init__(self) -> None:
        missing = TRADE_REQUIRED_COLS - set(self.df.columns)
        if missing:
            msg = f"Missing required columns: {sorted(missing)}"
            raise ValueError(msg)


class MarketDataProvider(Protocol):
    """Protocol for market data sources (e.g., Kraken adapter).

    The signal engine depends on this interface, not on a concrete
    Kraken implementation. Any object with these async methods works.
    """

    async def ticker(self, pair: str) -> TickerData: ...

    async def ohlc(
        self, pair: str, interval: int
    ) -> OHLCData: ...

    async def orderbook(
        self, pair: str, count: int
    ) -> OrderBookSnapshot: ...

    async def recent_trades(
        self, pair: str
    ) -> TradeFlowData: ...
