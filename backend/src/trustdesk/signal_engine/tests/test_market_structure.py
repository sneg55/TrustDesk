"""Tests for market structure analysis."""

from __future__ import annotations

import pandas as pd
import pytest

from trustdesk.signal_engine.market_structure import (
    compute_book_imbalance,
    compute_spread_pct,
    compute_trade_flow_direction,
)
from trustdesk.signal_engine.types import (
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


class TestBookImbalance:
    """Order book imbalance ratio tests."""

    def test_bullish_imbalance(
        self, bullish_orderbook: OrderBookSnapshot
    ) -> None:
        ratio = compute_book_imbalance(bullish_orderbook)
        assert ratio > 0.55

    def test_balanced_book(
        self, balanced_orderbook: OrderBookSnapshot
    ) -> None:
        ratio = compute_book_imbalance(balanced_orderbook)
        assert ratio == pytest.approx(0.5)

    def test_ratio_bounded(
        self, bullish_orderbook: OrderBookSnapshot
    ) -> None:
        ratio = compute_book_imbalance(bullish_orderbook)
        assert 0.0 <= ratio <= 1.0


class TestTradeFlow:
    """Trade flow direction tests."""

    def test_buy_heavy_positive(
        self, buy_heavy_trades: TradeFlowData
    ) -> None:
        direction = compute_trade_flow_direction(buy_heavy_trades)
        assert direction > 0.0

    def test_direction_bounded(
        self, buy_heavy_trades: TradeFlowData
    ) -> None:
        direction = compute_trade_flow_direction(buy_heavy_trades)
        assert -1.0 <= direction <= 1.0


class TestSpread:
    """Spread percentage tests."""

    def test_spread_pct(self, sample_ticker: TickerData) -> None:
        spread = compute_spread_pct(sample_ticker)
        expected = (100.0 / 50050.0) * 100
        assert spread == pytest.approx(expected)

    def test_spread_positive(self, sample_ticker: TickerData) -> None:
        spread = compute_spread_pct(sample_ticker)
        assert spread > 0.0


class TestEdgeCases:
    """Edge cases for market structure functions."""

    def test_zero_volume_book(self) -> None:
        book = OrderBookSnapshot(
            pair="BTCUSD",
            asks=pd.DataFrame({"price": [100.0], "volume": [0.0]}),
            bids=pd.DataFrame({"price": [99.0], "volume": [0.0]}),
        )
        assert compute_book_imbalance(book) == 0.5

    def test_zero_volume_trades(self) -> None:
        trades = TradeFlowData(
            pair="BTCUSD",
            df=pd.DataFrame(
                {
                    "price": [100.0],
                    "volume": [0.0],
                    "time": [1.0],
                    "side": ["buy"],
                }
            ),
        )
        assert compute_trade_flow_direction(trades) == 0.0
