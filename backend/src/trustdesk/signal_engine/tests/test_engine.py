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


def _make_mock_strykr() -> AsyncMock:
    """Create a mock StrykrClient."""
    client = AsyncMock()
    client.signals.return_value = {
        "overall_signal": "bullish",
        "direction": "bullish",
        "strength": "moderate",
        "net_score": 1,
    }
    client.risk.return_value = {
        "daily_volatility": 0.55,
        "current_drawdown": 0.52,
        "sharpe_ratio": -0.86,
    }
    return client


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


class TestSignalEngineStrykr:
    """Tests for Strykr/PRISM integration in the signal engine."""

    @pytest.mark.asyncio()
    async def test_run_cycle_without_strykr(self) -> None:
        """Engine works exactly as before when strykr=None."""
        provider = _mock_provider()
        engine = SignalEngine(provider=provider, strykr=None)
        signal = await engine.run_cycle("BTC/USD")
        assert isinstance(signal, SignalPayload)
        assert "prism_overall_signal" not in signal.indicators

    @pytest.mark.asyncio()
    async def test_run_cycle_with_strykr(self) -> None:
        """Mock StrykrClient provides data merged into indicators dict."""
        provider = _mock_provider()
        mock_strykr = _make_mock_strykr()
        engine = SignalEngine(provider=provider, strykr=mock_strykr)
        signal = await engine.run_cycle("BTC/USD")
        mock_strykr.signals.assert_awaited_once_with("BTC")
        mock_strykr.risk.assert_awaited_once_with("BTC")
        assert signal.indicators["prism_overall_signal"] == "bullish"
        assert signal.indicators["prism_direction"] == "bullish"
        assert signal.indicators["prism_strength"] == "moderate"
        assert signal.indicators["prism_net_score"] == 1
        assert signal.indicators["prism_daily_volatility"] == 0.55
        assert signal.indicators["prism_current_drawdown"] == 0.52
        assert signal.indicators["prism_sharpe_ratio"] == -0.86

    @pytest.mark.asyncio()
    async def test_run_cycle_strykr_signals_failure(self) -> None:
        """Engine continues when strykr.signals() raises an exception."""
        provider = _mock_provider()
        mock_strykr = _make_mock_strykr()
        mock_strykr.signals.side_effect = Exception("API down")
        engine = SignalEngine(provider=provider, strykr=mock_strykr)
        signal = await engine.run_cycle("BTC/USD")
        assert "prism_overall_signal" not in signal.indicators
        assert "prism_direction" not in signal.indicators
        # risk should still work since it's a separate try/except
        assert signal.indicators["prism_daily_volatility"] == 0.55

    @pytest.mark.asyncio()
    async def test_run_cycle_strykr_risk_failure(self) -> None:
        """Engine continues when strykr.risk() raises an exception."""
        provider = _mock_provider()
        mock_strykr = _make_mock_strykr()
        mock_strykr.risk.side_effect = Exception("API down")
        engine = SignalEngine(provider=provider, strykr=mock_strykr)
        signal = await engine.run_cycle("BTC/USD")
        assert signal.indicators["prism_overall_signal"] == "bullish"
        assert "prism_daily_volatility" not in signal.indicators
        assert "prism_sharpe_ratio" not in signal.indicators

    @pytest.mark.asyncio()
    async def test_run_cycle_symbol_extraction(self) -> None:
        """Base symbol is correctly extracted from pair for strykr call."""
        provider = _mock_provider()
        mock_strykr = _make_mock_strykr()
        engine = SignalEngine(provider=provider, strykr=mock_strykr)
        await engine.run_cycle("ETH/USD")
        mock_strykr.signals.assert_awaited_once_with("ETH")
        mock_strykr.risk.assert_awaited_once_with("ETH")

    @pytest.mark.asyncio()
    async def test_run_cycle_strykr_no_slash_pair(self) -> None:
        """Pair without slash passes entire string as symbol."""
        provider = _mock_provider()
        mock_strykr = _make_mock_strykr()
        engine = SignalEngine(provider=provider, strykr=mock_strykr)
        await engine.run_cycle("BTCUSD")
        mock_strykr.signals.assert_awaited_once_with("BTCUSD")
        mock_strykr.risk.assert_awaited_once_with("BTCUSD")
