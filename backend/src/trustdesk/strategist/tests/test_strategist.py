"""Tests for the Strategist module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.strategist.strategist import Strategist, StrategistProposal, decision_to_proposal
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


def _make_signal(
    alignment_score: float = 0.85,
    regime: str = "TRENDING_UP",
    pair: str = "BTC/USD",
) -> MagicMock:
    signal = MagicMock()
    signal.alignment_score = alignment_score
    signal.regime = regime
    signal.pair = pair
    signal.model_dump.return_value = {
        "pair": pair,
        "alignment_score": alignment_score,
        "regime": regime,
    }
    return signal


class TestStrategistEvaluate:
    @pytest.mark.asyncio
    async def test_no_signal_returns_pass(self) -> None:
        client = AsyncMock()
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.30)

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert result.decision == DecisionType.PASS
        assert "0.3" in result.reasoning
        client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_trending_down_returns_pass(self) -> None:
        client = AsyncMock()
        strategist = Strategist(client)
        signal = _make_signal(regime="TRENDING_DOWN")

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert "TRENDING_DOWN" in result.reasoning
        client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_propose_response(self) -> None:
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Strong pullback entry on BTC.",
            "pair": "BTC/USD",
            "side": "buy",
            "confidence": 0.9,
            "position_size_pct": 0.8,
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.85)

        result = await strategist.evaluate(signal)

        assert isinstance(result, StrategistDecision)
        assert result.decision == DecisionType.PROPOSE
        assert result.pair == "BTC/USD"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_llm_pass_response(self) -> None:
        llm_response = json.dumps({
            "decision": "PASS",
            "reasoning": "No clear signal.",
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal()

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert result.reasoning == "No clear signal."

    @pytest.mark.asyncio
    async def test_invalid_json_returns_pass(self) -> None:
        client = AsyncMock()
        client.complete.return_value = "this is not json"
        strategist = Strategist(client)
        signal = _make_signal()

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert "not valid JSON" in result.reasoning

    @pytest.mark.asyncio
    async def test_weak_signal_without_override_returns_pass(self) -> None:
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Taking a chance.",
            "pair": "ETH/USD",
            "side": "buy",
            "confidence": 0.7,
            "position_size_pct": 0.5,
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.55)

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert "override_justification" in result.reasoning

    @pytest.mark.asyncio
    async def test_volatile_regime_halves_position_size(self) -> None:
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Strong signal in vol regime.",
            "pair": "BTC/USD",
            "side": "buy",
            "confidence": 1.0,
            "position_size_pct": 1.0,
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(
            alignment_score=1.0,
            regime="VOLATILE",
        )

        result = await strategist.evaluate(signal)

        assert isinstance(result, StrategistDecision)
        assert result.position_size_pct == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_llm_propose_missing_fields_uses_defaults(self) -> None:
        """Test that missing fields in LLM response use safe defaults."""
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Good entry.",
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.85)

        result = await strategist.evaluate(signal)

        assert isinstance(result, StrategistDecision)
        assert result.pair == "BTC/USD"  # falls back to signal.pair
        assert result.side == "buy"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_exact_no_signal_threshold_returns_pass(self) -> None:
        """Alignment score exactly at 0.40 is still a PASS (<=)."""
        client = AsyncMock()
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.40)

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        client.complete.assert_not_called()


class TestDecisionToProposal:
    def test_converts_decision_to_proposal(self) -> None:
        decision = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )
        signal = _make_signal()

        proposal = decision_to_proposal(decision, signal, agent_id="agent-1")

        assert isinstance(proposal, StrategistProposal)
        assert proposal.pair == "BTC/USD"
        assert proposal.agent_id == "agent-1"
        assert proposal.confidence == 0.9

    def test_model_dump_returns_dict(self) -> None:
        decision = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Entry.",
            pair="ETH/USD",
            side="buy",
            confidence=0.8,
            position_size_pct=0.5,
            override_justification="weak signal OK",
        )
        signal = _make_signal(pair="ETH/USD", regime="RANGING")

        proposal = decision_to_proposal(decision, signal, agent_id="agent-2")
        dumped = proposal.model_dump(mode="json")

        assert dumped["pair"] == "ETH/USD"
        assert dumped["agent_id"] == "agent-2"
        assert dumped["override_justification"] == "weak signal OK"
