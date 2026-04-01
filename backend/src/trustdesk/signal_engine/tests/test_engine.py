"""Tests for the main signal engine cycle."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pandas as pd
import pytest

from trustdesk.schemas.signal_payload import Alignment, SignalPayload
from trustdesk.signal_engine.engine import SignalEngine
from trustdesk.signal_engine.tests.conftest import _make_ohlc_df
from trustdesk.signal_engine.types import (
    OHLCData,
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


def _mock_provider(
    pair: str = "BTCUSD",
    trend: float = 0.002,
    seed: int = 42,
) -> AsyncMock:
    """Create a mock MarketDataProvider."""
    provider = AsyncMock()

    ohlc_df = _make_ohlc_df(n=60, trend=trend, seed=seed)
    provider.ticker.return_value = TickerData(
        pair=pair,
        ask=float(ohlc_df["close"].iloc[-1]) + 50,
        bid=float(ohlc_df["close"].iloc[-1]) - 50,
        last=float(ohlc_df["close"].iloc[-1]),
        volume_today=1500.0,
        vwap_today=float(ohlc_df["vwap"].iloc[-1]),
    )

    async def mock_ohlc(p: str, interval: int) -> OHLCData:
        return OHLCData(pair=p, interval=interval, df=ohlc_df.copy())

    provider.ohlc.side_effect = mock_ohlc

    provider.orderbook.return_value = OrderBookSnapshot(
        pair=pair,
        asks=pd.DataFrame(
            {
                "price": [
                    float(ohlc_df["close"].iloc[-1]) + 10 * i
                    for i in range(1, 26)
                ],
                "volume": [0.5] * 25,
            }
        ),
        bids=pd.DataFrame(
            {
                "price": [
                    float(ohlc_df["close"].iloc[-1]) - 10 * i
                    for i in range(1, 26)
                ],
                "volume": [1.5] * 25,
            }
        ),
    )

    provider.recent_trades.return_value = TradeFlowData(
        pair=pair,
        df=pd.DataFrame(
            {
                "price": [
                    float(ohlc_df["close"].iloc[-1]) + i
                    for i in range(20)
                ],
                "volume": [1.0] * 20,
                "time": [float(i) for i in range(20)],
                "side": ["buy"] * 15 + ["sell"] * 5,
            }
        ),
    )
    return provider


class TestSignalEngine:
    """Main engine cycle tests."""

    @pytest.mark.asyncio()
    async def test_run_cycle_returns_payload(self) -> None:
        provider = _mock_provider(trend=0.002)
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert isinstance(payload, SignalPayload)

    @pytest.mark.asyncio()
    async def test_payload_has_pair(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.pair == "BTCUSD"

    @pytest.mark.asyncio()
    async def test_payload_has_regime(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.regime in (
            "TRENDING_UP",
            "TRENDING_DOWN",
            "RANGING",
            "VOLATILE",
        )

    @pytest.mark.asyncio()
    async def test_payload_has_alignment(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.alignment in (
            Alignment.STRONG,
            Alignment.MODERATE,
            Alignment.WEAK,
            Alignment.NO_SIGNAL,
        )

    @pytest.mark.asyncio()
    async def test_payload_has_derived_values(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.derived.suggested_stop_distance > 0
        assert payload.derived.position_size_pct >= 0
        assert isinstance(payload.derived.regime_aligned, bool)

    @pytest.mark.asyncio()
    async def test_payload_has_score(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert 0.0 <= payload.alignment_score <= 1.0

    @pytest.mark.asyncio()
    async def test_downtrend_provider(self) -> None:
        provider = _mock_provider(trend=-0.002)
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert isinstance(payload, SignalPayload)

    @pytest.mark.asyncio()
    async def test_provider_called_correctly(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        await engine.run_cycle("BTCUSD")
        provider.ticker.assert_called_once_with("BTCUSD")
        assert provider.ohlc.call_count == 3  # 15m, 1H, 4H
        provider.orderbook.assert_called_once_with("BTCUSD", count=25)
        provider.recent_trades.assert_called_once_with("BTCUSD")
