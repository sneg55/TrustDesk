"""Tests for signal engine internal types."""

from __future__ import annotations

import pandas as pd
import pytest

from trustdesk.signal_engine.types import (
    CrossoverState,
    OBVTrend,
    OHLCData,
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


class TestOHLCData:
    """OHLCData validation and construction."""

    def test_valid_ohlc(self) -> None:
        data = OHLCData(
            pair="BTCUSD",
            interval=15,
            df=pd.DataFrame(
                {
                    "timestamp": [1.0, 2.0],
                    "open": [100.0, 101.0],
                    "high": [102.0, 103.0],
                    "low": [99.0, 100.0],
                    "close": [101.0, 102.0],
                    "volume": [10.0, 11.0],
                    "vwap": [100.5, 101.5],
                    "count": [5, 6],
                }
            ),
        )
        assert data.pair == "BTCUSD"
        assert data.interval == 15
        assert len(data.df) == 2

    def test_missing_column_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing required columns"):
            OHLCData(
                pair="BTCUSD",
                interval=15,
                df=pd.DataFrame({"open": [1.0], "close": [2.0]}),
            )


class TestTickerData:
    """TickerData construction."""

    def test_valid_ticker(self) -> None:
        t = TickerData(
            pair="BTCUSD",
            ask=100.5,
            bid=100.0,
            last=100.2,
            volume_today=1500.0,
            vwap_today=100.1,
        )
        assert t.spread == pytest.approx(0.5)
        assert t.spread_pct == pytest.approx(0.5 / 100.2 * 100)


class TestOrderBookSnapshot:
    """OrderBookSnapshot construction."""

    def test_valid_book(self) -> None:
        book = OrderBookSnapshot(
            pair="BTCUSD",
            asks=pd.DataFrame(
                {"price": [101.0, 102.0], "volume": [1.0, 2.0]}
            ),
            bids=pd.DataFrame(
                {"price": [100.0, 99.0], "volume": [1.5, 2.5]}
            ),
        )
        assert len(book.asks) == 2
        assert len(book.bids) == 2


class TestTradeFlowData:
    """TradeFlowData construction."""

    def test_valid_trade_flow(self) -> None:
        tf = TradeFlowData(
            pair="BTCUSD",
            df=pd.DataFrame(
                {
                    "price": [100.0, 101.0],
                    "volume": [1.0, 2.0],
                    "time": [1.0, 2.0],
                    "side": ["buy", "sell"],
                }
            ),
        )
        assert len(tf.df) == 2

    def test_missing_column_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing required columns"):
            TradeFlowData(
                pair="BTCUSD",
                df=pd.DataFrame({"price": [100.0]}),
            )


class TestEnums:
    """Enum types."""

    def test_crossover_state_values(self) -> None:
        assert CrossoverState.BULLISH.value == "BULLISH"
        assert CrossoverState.BEARISH.value == "BEARISH"
        assert CrossoverState.NEUTRAL.value == "NEUTRAL"

    def test_obv_trend_values(self) -> None:
        assert OBVTrend.RISING.value == "RISING"
        assert OBVTrend.FALLING.value == "FALLING"
        assert OBVTrend.FLAT.value == "FLAT"
