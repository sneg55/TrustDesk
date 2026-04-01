"""Shared fixtures for signal engine tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trustdesk.signal_engine.types import (
    OHLCData,
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


def _make_ohlc_df(
    n: int = 60,
    base_price: float = 50000.0,
    trend: float = 0.001,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic OHLC data with optional trend."""
    rng = np.random.default_rng(seed)
    timestamps = np.arange(n, dtype=float)
    closes = np.empty(n)
    closes[0] = base_price
    for i in range(1, n):
        ret = trend + rng.normal(0, 0.005)
        closes[i] = closes[i - 1] * (1 + ret)

    opens = closes * (1 + rng.normal(0, 0.001, n))
    highs = np.maximum(opens, closes) * (1 + rng.uniform(0, 0.005, n))
    lows = np.minimum(opens, closes) * (1 - rng.uniform(0, 0.005, n))
    volumes = rng.uniform(100, 500, n)
    vwaps = (highs + lows + closes) / 3
    counts = rng.integers(50, 200, n)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "vwap": vwaps,
            "count": counts,
        }
    )


@pytest.fixture()
def uptrend_ohlc() -> OHLCData:
    """60 candles with an uptrend (0.2% per bar)."""
    return OHLCData(
        pair="BTCUSD",
        interval=15,
        df=_make_ohlc_df(n=60, trend=0.002, seed=42),
    )


@pytest.fixture()
def downtrend_ohlc() -> OHLCData:
    """60 candles with a downtrend (-0.2% per bar)."""
    return OHLCData(
        pair="BTCUSD",
        interval=15,
        df=_make_ohlc_df(n=60, trend=-0.002, seed=42),
    )


@pytest.fixture()
def ranging_ohlc() -> OHLCData:
    """60 candles with no trend (flat)."""
    return OHLCData(
        pair="BTCUSD",
        interval=15,
        df=_make_ohlc_df(n=60, trend=0.0, seed=42),
    )


@pytest.fixture()
def volatile_ohlc() -> OHLCData:
    """60 candles with high volatility."""
    df = _make_ohlc_df(n=60, trend=0.0, seed=42)
    df["high"] = df["high"] * 1.02
    df["low"] = df["low"] * 0.98
    return OHLCData(pair="BTCUSD", interval=15, df=df)


@pytest.fixture()
def sample_ticker() -> TickerData:
    """A sample ticker snapshot."""
    return TickerData(
        pair="BTCUSD",
        ask=50100.0,
        bid=50000.0,
        last=50050.0,
        volume_today=1500.0,
        vwap_today=50025.0,
    )


@pytest.fixture()
def bullish_orderbook() -> OrderBookSnapshot:
    """Order book with stronger bids (bullish imbalance)."""
    return OrderBookSnapshot(
        pair="BTCUSD",
        asks=pd.DataFrame(
            {
                "price": [50100.0 + i * 10 for i in range(25)],
                "volume": [0.5] * 25,
            }
        ),
        bids=pd.DataFrame(
            {
                "price": [50000.0 - i * 10 for i in range(25)],
                "volume": [1.5] * 25,
            }
        ),
    )


@pytest.fixture()
def balanced_orderbook() -> OrderBookSnapshot:
    """Order book with balanced bids and asks."""
    return OrderBookSnapshot(
        pair="BTCUSD",
        asks=pd.DataFrame(
            {
                "price": [50100.0 + i * 10 for i in range(25)],
                "volume": [1.0] * 25,
            }
        ),
        bids=pd.DataFrame(
            {
                "price": [50000.0 - i * 10 for i in range(25)],
                "volume": [1.0] * 25,
            }
        ),
    )


@pytest.fixture()
def buy_heavy_trades() -> TradeFlowData:
    """Recent trades dominated by buy-side."""
    return TradeFlowData(
        pair="BTCUSD",
        df=pd.DataFrame(
            {
                "price": [50050.0 + i for i in range(20)],
                "volume": [1.0] * 20,
                "time": [float(i) for i in range(20)],
                "side": ["buy"] * 15 + ["sell"] * 5,
            }
        ),
    )
