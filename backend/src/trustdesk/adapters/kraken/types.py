"""Data types for Kraken CLI adapter."""
from __future__ import annotations

from pydantic import BaseModel, computed_field


class TickerData(BaseModel):
    """Ticker snapshot for a trading pair."""

    pair: str
    ask: float
    bid: float
    last: float
    volume_24h: float
    high_24h: float
    low_24h: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spread(self) -> float:
        return self.ask - self.bid


class Candle(BaseModel):
    """Single OHLCV candle."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class OrderBookEntry(BaseModel):
    """Single order book level."""

    price: float
    volume: float


class OrderBook(BaseModel):
    """Order book snapshot."""

    pair: str
    asks: list[OrderBookEntry]
    bids: list[OrderBookEntry]


class Trade(BaseModel):
    """Recent trade entry."""

    price: float
    volume: float
    time: float
    side: str


class Order(BaseModel):
    """Open order."""

    order_id: str
    pair: str
    side: str
    order_type: str
    price: float
    volume: float
    status: str


class OrderResult(BaseModel):
    """Result from placing an order."""

    order_id: str
    status: str
    description: str


class TradeRecord(BaseModel):
    """Historical trade record."""

    trade_id: str
    pair: str
    side: str
    price: float
    volume: float
    cost: float
    fee: float
    time: float
