"""Tests for AnthropicClient."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.adapters.anthropic.client import AnthropicClient
from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.errors import LLMUnavailableError
from trustdesk.schemas.proposal import TradeProposal
from trustdesk.schemas.signal_payload import (
    Alignment,
    AlignmentBreakdown,
    DerivedValues,
    SignalPayload,
)


def _config() -> TrustDeskConfig:
    return TrustDeskConfig(
        anthropic_api_key="test-key",
        trustdesk_agent_private_key="0x" + "ab" * 32,
        trustdesk_validator_private_key="0x" + "cd" * 32,
    )


def _signal() -> SignalPayload:
    return SignalPayload(
        pair="BTC/USD",
        price=50000.0,
        regime="TRENDING_UP",
        alignment=Alignment.STRONG,
        alignment_score=0.8,
        breakdown=AlignmentBreakdown(
            ema_crossover=True,
            adx_trending=True,
            volume_confirmed=True,
            obv_aligned=True,
            book_imbalance_aligned=False,
        ),
        derived=DerivedValues(
            suggested_stop_distance=0.03,
            position_size_pct=0.05,
            regime_aligned=True,
        ),
        indicators={"ema_9": 49800.0, "adx_14": 30.0},
    )


def _proposal() -> TradeProposal:
    return TradeProposal(
        agent_id="agent-1",
        proposal_id="prop-1",
        timestamp=datetime(2026, 1, 1),
        action="BUY",
        pair="BTC/USD",
        size_pct=0.05,
        entry_price_limit=50000.0,
        stop_loss=48500.0,
        take_profit_1=52000.0,
        time_horizon="4h",
        reasoning="Strong uptrend with alignment.",
        invalidation="Price below 48000",
    )


PROPOSAL_JSON: dict[str, Any] = {
    "agent_id": "agent-1",
    "proposal_id": "prop-1",
    "timestamp": "2026-01-01T00:00:00",
    "action": "BUY",
    "pair": "BTC/USD",
    "size_pct": 0.05,
    "entry_price_limit": 50000.0,
    "entry_type": "LIMIT",
    "stop_loss": 48500.0,
    "take_profit_1": 52000.0,
    "time_horizon": "4h",
    "reasoning": "Strong uptrend with alignment.",
    "invalidation": "Price below 48000",
}


def _mock_response(content: str) -> MagicMock:
    """Create a mock Anthropic response."""
    msg = MagicMock()
    block = MagicMock()
    block.text = content
    msg.content = [block]
    return msg


class TestAnthropicClientStrategist:
    async def test_strategist_returns_proposal(self) -> None:
        mock_anthropic = MagicMock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = MagicMock()
        mock_anthropic.messages.create = mock_messages
        mock_messages.return_value = _mock_response(json.dumps(PROPOSAL_JSON))

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())
            result = await client.strategist_evaluate(_signal(), {"balance_usd": 10000})

        assert result is not None
        assert result.action == "BUY"
        assert result.pair == "BTC/USD"
        assert result.size_pct == 0.05

    async def test_strategist_returns_none_on_pass(self) -> None:
        mock_anthropic = MagicMock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = MagicMock()
        mock_anthropic.messages.create = mock_messages
        mock_messages.return_value = _mock_response('{"action": "PASS"}')

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())
            result = await client.strategist_evaluate(_signal(), {"balance_usd": 10000})

        assert result is None


class TestAnthropicClientRisk:
    async def test_risk_evaluate_soft_returns_checks(self) -> None:
        checks = {"position_sizing": "OK", "drawdown_risk": "LOW"}
        mock_anthropic = MagicMock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = MagicMock()
        mock_anthropic.messages.create = mock_messages
        mock_messages.return_value = _mock_response(json.dumps(checks))

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())
            result = await client.risk_evaluate_soft(_proposal(), {"balance_usd": 10000})

        assert result == {"position_sizing": "OK", "drawdown_risk": "LOW"}


class TestAnthropicClientCircuitBreaker:
    async def test_circuit_opens_after_three_failures(self) -> None:
        mock_anthropic = MagicMock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = MagicMock()
        mock_anthropic.messages.create = mock_messages

        api_error = Exception("API connection error")
        mock_messages.side_effect = api_error

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())
            assert client.is_available() is True

            for _ in range(3):
                with pytest.raises(LLMUnavailableError):
                    await client.strategist_evaluate(_signal(), {})

            assert client.is_available() is False

    async def test_circuit_recovers_after_cooldown(self) -> None:
        mock_anthropic = MagicMock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = MagicMock()
        mock_anthropic.messages.create = mock_messages
        mock_messages.side_effect = Exception("API error")

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())
            # Use a very short cooldown so we can test recovery
            client._cooldown_seconds = 0.05

            for _ in range(3):
                with pytest.raises(LLMUnavailableError):
                    await client.strategist_evaluate(_signal(), {})

            # Circuit just opened — should not be available yet
            assert client._available is False

            # After cooldown, circuit should auto-recover
            time.sleep(0.1)
            assert client.is_available() is True

    async def test_success_resets_failure_count(self) -> None:
        mock_anthropic = MagicMock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = MagicMock()
        mock_anthropic.messages.create = mock_messages

        # Fail twice then succeed
        api_error = Exception("API error")
        mock_messages.side_effect = [
            api_error,
            api_error,
            _mock_response(json.dumps(PROPOSAL_JSON)),
        ]

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())

            with pytest.raises(LLMUnavailableError):
                await client.strategist_evaluate(_signal(), {})
            with pytest.raises(LLMUnavailableError):
                await client.strategist_evaluate(_signal(), {})

            # Third call succeeds, resets counter
            result = await client.strategist_evaluate(_signal(), {})
            assert result is not None
            assert client.is_available() is True
            assert client._consecutive_failures == 0


class TestAnthropicClientUnavailable:
    async def test_call_when_circuit_open_raises(self) -> None:
        mock_anthropic = MagicMock()

        with patch("trustdesk.adapters.anthropic.client.AsyncAnthropic", return_value=mock_anthropic):
            client = AnthropicClient(_config())
            client._available = False
            client._cooldown_seconds = 9999.0
            client._opened_at = time.monotonic()

            with pytest.raises(LLMUnavailableError, match="circuit breaker open"):
                await client.strategist_evaluate(_signal(), {})
