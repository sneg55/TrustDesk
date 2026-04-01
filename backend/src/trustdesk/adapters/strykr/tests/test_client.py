"""Tests for StrykrClient — mocks httpx at the transport level."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.adapters.strykr.client import StrykrClient
from trustdesk.adapters.strykr.types import PrismRisk, PrismSignal, ResolvedAsset

# ---------------------------------------------------------------------------
# Fixture data matching real API responses
# ---------------------------------------------------------------------------

_RESOLVE_RESPONSE = {
    "object": "resolved_asset",
    "id": "asset-token-btc-ticker-fast-btc",
    "symbol": "BTC",
    "name": "Bitcoin",
    "type": "crypto",
    "confidence": 0.9,
    "resolution_path": "cache",
    "latency_ms": 4.8,
    "venues": {
        "object": "list",
        "data": [{"id": "binance", "name": "Binance", "type": "cex_spot"}],
    },
}

_SIGNALS_RESPONSE = {
    "object": "list",
    "data": [
        {
            "symbol": "BTC",
            "overall_signal": "bullish",
            "direction": "bullish",
            "strength": "moderate",
            "bullish_score": 1,
            "bearish_score": 0,
            "net_score": 1,
            "current_price": 68732.54,
            "indicators": {
                "rsi": 55.71,
                "macd": 207.13,
                "macd_histogram": 284.61,
                "bollinger_upper": 69191.46,
                "bollinger_lower": 65621.74,
            },
            "active_signals": [{"type": "macd", "signal": "bullish", "value": 284.61}],
            "signal_count": 1,
            "timestamp": "2026-04-01T17:19:02Z",
        }
    ],
}

_RISK_RESPONSE = {
    "object": "stats",
    "symbol": "BTC",
    "daily_volatility": 0.5498,
    "annual_volatility": 8.73,
    "sharpe_ratio": -0.863,
    "sortino_ratio": -0.839,
    "max_drawdown": 35.59,
    "current_drawdown": 0.52,
    "avg_daily_return": -0.01,
    "positive_days_pct": 49.3,
    "timestamp": "2026-04-01T17:14:34Z",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status: int, json_data: dict) -> MagicMock:
    """Return a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    else:
        resp.raise_for_status = MagicMock()
    return resp


def _patched_client(get_return_value: MagicMock) -> tuple[StrykrClient, MagicMock]:
    """Create a StrykrClient whose inner _client.get is pre-configured."""
    client = StrykrClient(api_key="test-key")
    mock_inner = AsyncMock()
    mock_inner.get = AsyncMock(return_value=get_return_value)
    client._client = mock_inner
    return client, mock_inner


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------

class TestResolve:
    async def test_resolve_returns_resolved_asset(self) -> None:
        client, _ = _patched_client(_mock_response(200, _RESOLVE_RESPONSE))
        result = await client.resolve("BTC")
        assert isinstance(result, ResolvedAsset)
        assert result.symbol == "BTC"
        assert result.name == "Bitcoin"
        assert result.type == "crypto"
        assert result.confidence == 0.9
        assert result.venues == [{"id": "binance", "name": "Binance", "type": "cex_spot"}]

    async def test_resolve_calls_correct_endpoint(self) -> None:
        client, mock_inner = _patched_client(_mock_response(200, _RESOLVE_RESPONSE))
        await client.resolve("ETH")
        mock_inner.get.assert_called_once_with("/resolve/ETH")

    async def test_resolve_raises_on_http_error(self) -> None:
        client, _ = _patched_client(_mock_response(404, {"error": "not found"}))
        with pytest.raises(Exception, match="HTTP 404"):
            await client.resolve("UNKNOWN")

    async def test_resolve_empty_venues(self) -> None:
        data = {**_RESOLVE_RESPONSE, "venues": {"object": "list", "data": []}}
        client, _ = _patched_client(_mock_response(200, data))
        result = await client.resolve("BTC")
        assert result.venues == []


# ---------------------------------------------------------------------------
# signals()
# ---------------------------------------------------------------------------

class TestSignals:
    async def test_signals_returns_prism_signal(self) -> None:
        client, _ = _patched_client(_mock_response(200, _SIGNALS_RESPONSE))
        result = await client.signals("BTC")
        assert isinstance(result, PrismSignal)
        assert result.symbol == "BTC"
        assert result.overall_signal == "bullish"
        assert result.direction == "bullish"
        assert result.strength == "moderate"
        assert result.bullish_score == 1
        assert result.bearish_score == 0
        assert result.net_score == 1
        assert result.current_price == 68732.54

    async def test_signals_indicators_parsed(self) -> None:
        client, _ = _patched_client(_mock_response(200, _SIGNALS_RESPONSE))
        result = await client.signals("BTC")
        assert result.indicators.rsi == pytest.approx(55.71)
        assert result.indicators.macd == pytest.approx(207.13)
        assert result.indicators.macd_histogram == pytest.approx(284.61)
        assert result.indicators.bollinger_upper == pytest.approx(69191.46)
        assert result.indicators.bollinger_lower == pytest.approx(65621.74)

    async def test_signals_active_signals_parsed(self) -> None:
        client, _ = _patched_client(_mock_response(200, _SIGNALS_RESPONSE))
        result = await client.signals("BTC")
        assert len(result.active_signals) == 1
        assert result.active_signals[0]["type"] == "macd"

    async def test_signals_calls_correct_endpoint(self) -> None:
        client, mock_inner = _patched_client(_mock_response(200, _SIGNALS_RESPONSE))
        await client.signals("ETH")
        mock_inner.get.assert_called_once_with("/signals/ETH")

    async def test_signals_raises_on_http_error(self) -> None:
        client, _ = _patched_client(_mock_response(500, {"error": "internal error"}))
        with pytest.raises(Exception, match="HTTP 500"):
            await client.signals("BTC")


# ---------------------------------------------------------------------------
# risk()
# ---------------------------------------------------------------------------

class TestRisk:
    async def test_risk_returns_prism_risk(self) -> None:
        client, _ = _patched_client(_mock_response(200, _RISK_RESPONSE))
        result = await client.risk("BTC")
        assert isinstance(result, PrismRisk)
        assert result.symbol == "BTC"
        assert result.daily_volatility == pytest.approx(0.5498)
        assert result.annual_volatility == pytest.approx(8.73)
        assert result.sharpe_ratio == pytest.approx(-0.863)
        assert result.sortino_ratio == pytest.approx(-0.839)
        assert result.max_drawdown == pytest.approx(35.59)
        assert result.current_drawdown == pytest.approx(0.52)

    async def test_risk_calls_correct_endpoint(self) -> None:
        client, mock_inner = _patched_client(_mock_response(200, _RISK_RESPONSE))
        await client.risk("ETH")
        mock_inner.get.assert_called_once_with("/risk/ETH")

    async def test_risk_raises_on_http_error(self) -> None:
        client, _ = _patched_client(_mock_response(503, {"error": "unavailable"}))
        with pytest.raises(Exception, match="HTTP 503"):
            await client.risk("BTC")


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    async def test_close_calls_aclose(self) -> None:
        client = StrykrClient(api_key="test-key")
        mock_inner = AsyncMock()
        client._client = mock_inner
        await client.close()
        mock_inner.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# __init__ / constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_constructor_sets_api_key_header(self) -> None:
        with patch("trustdesk.adapters.strykr.client.httpx.AsyncClient") as mock_cls:
            StrykrClient(api_key="my-secret-key")
            mock_cls.assert_called_once_with(
                base_url="https://api.prismapi.ai",
                headers={"X-API-Key": "my-secret-key"},
                timeout=10.0,
            )
