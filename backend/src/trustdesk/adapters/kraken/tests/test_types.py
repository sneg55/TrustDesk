"""Tests for Kraken data types."""
from __future__ import annotations

from trustdesk.adapters.kraken.types import (
    Candle,
    Order,
    OrderBook,
    OrderBookEntry,
    OrderResult,
    TickerData,
    Trade,
    TradeRecord,
)


class TestTickerData:
    def test_from_values(self) -> None:
        t = TickerData(pair="BTC/USD", ask=50100.0, bid=50000.0, last=50050.0, volume_24h=1234.5, high_24h=51000.0, low_24h=49000.0)
        assert t.pair == "BTC/USD"
        assert t.ask == 50100.0
        assert t.bid == 50000.0
        assert t.last == 50050.0
        assert t.volume_24h == 1234.5
        assert t.high_24h == 51000.0
        assert t.low_24h == 49000.0

    def test_spread(self) -> None:
        t = TickerData(pair="BTC/USD", ask=50100.0, bid=50000.0, last=50050.0, volume_24h=0.0, high_24h=0.0, low_24h=0.0)
        assert t.spread == 100.0


class TestCandle:
    def test_fields(self) -> None:
        c = Candle(timestamp=1000, open=100.0, high=110.0, low=90.0, close=105.0, volume=50.0)
        assert c.timestamp == 1000
        assert c.open == 100.0
        assert c.close == 105.0


class TestOrderBook:
    def test_fields(self) -> None:
        ob = OrderBook(
            pair="ETH/USD",
            asks=[OrderBookEntry(price=3000.0, volume=1.5)],
            bids=[OrderBookEntry(price=2990.0, volume=2.0)],
        )
        assert ob.pair == "ETH/USD"
        assert len(ob.asks) == 1
        assert ob.asks[0].price == 3000.0
        assert ob.bids[0].volume == 2.0


class TestTrade:
    def test_fields(self) -> None:
        t = Trade(price=50000.0, volume=0.1, time=1234567890.0, side="buy")
        assert t.price == 50000.0
        assert t.side == "buy"


class TestOrder:
    def test_fields(self) -> None:
        o = Order(
            order_id="O-ABC",
            pair="BTC/USD",
            side="buy",
            order_type="limit",
            price=50000.0,
            volume=0.5,
            status="open",
        )
        assert o.order_id == "O-ABC"
        assert o.status == "open"


class TestOrderResult:
    def test_fields(self) -> None:
        r = OrderResult(order_id="O-XYZ", status="pending", description="Order placed")
        assert r.order_id == "O-XYZ"
        assert r.description == "Order placed"


class TestTradeRecord:
    def test_fields(self) -> None:
        tr = TradeRecord(
            trade_id="T-123",
            pair="BTC/USD",
            side="buy",
            price=50000.0,
            volume=0.1,
            cost=5000.0,
            fee=5.0,
            time=1234567890.0,
        )
        assert tr.trade_id == "T-123"
        assert tr.cost == 5000.0
        assert tr.fee == 5.0
