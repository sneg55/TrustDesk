"""Tests for orchestrator node functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.orchestrator.nodes import (
    audit_node,
    audit_pass_node,
    execute_node,
    reputation_node,
    risk_node,
    signal_engine_node,
    strategist_node,
)
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


class TestSignalEngineNode:
    @pytest.mark.asyncio
    async def test_populates_signal_payload(self) -> None:
        engine = AsyncMock()
        signal = MagicMock()
        signal.model_dump.return_value = {"pair": "BTC/USD", "alignment_score": 0.9}
        signal.regime.value = "TRENDING_UP"
        engine.generate.return_value = signal

        result = await signal_engine_node({}, engine=engine)

        assert result["signal_payload"]["pair"] == "BTC/USD"
        assert result["regime"] == "TRENDING_UP"

    @pytest.mark.asyncio
    async def test_regime_as_string_fallback(self) -> None:
        """When regime has no .value attribute, str() is used."""
        engine = AsyncMock()
        signal = MagicMock()
        signal.model_dump.return_value = {"pair": "BTC/USD"}
        # Simulate regime without .value
        del signal.regime.value
        signal.regime.__str__ = lambda self: "RANGING"
        engine.generate.return_value = signal

        result = await signal_engine_node({}, engine=engine)

        assert "regime" in result


class TestStrategistNode:
    @pytest.mark.asyncio
    async def test_pass_decision(self) -> None:
        strategist = AsyncMock()
        strategist.evaluate.return_value = PassDecision(
            decision=DecisionType.PASS,
            reasoning="No signal.",
        )
        signal_cls = MagicMock()
        signal_cls.model_validate.return_value = MagicMock()

        state = {"signal_payload": {"pair": "BTC/USD"}, "agent_id": "agent-1"}
        result = await strategist_node(state, strategist=strategist, signal_cls=signal_cls)

        assert result["decision_type"] == "PASS"
        assert result["proposal"] is None
        assert result["pass_reasoning"] == "No signal."

    @pytest.mark.asyncio
    async def test_propose_decision(self) -> None:
        decision = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )
        strategist = AsyncMock()
        strategist.evaluate.return_value = decision
        signal_cls = MagicMock()
        mock_signal = MagicMock()
        mock_signal.regime = "TRENDING_UP"
        signal_cls.model_validate.return_value = mock_signal

        mock_proposal = MagicMock()
        mock_proposal.model_dump.return_value = {"pair": "BTC/USD", "side": "buy"}

        state = {"signal_payload": {"pair": "BTC/USD"}, "agent_id": "agent-1"}

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mock_proposal,
        ):
            result = await strategist_node(state, strategist=strategist, signal_cls=signal_cls)

        assert result["decision_type"] == "PROPOSE"
        assert result["proposal"] is not None

    @pytest.mark.asyncio
    async def test_propose_decision_no_agent_id(self) -> None:
        """When agent_id is missing from state, 'unknown' is used."""
        decision = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )
        strategist = AsyncMock()
        strategist.evaluate.return_value = decision
        signal_cls = MagicMock()
        mock_signal = MagicMock()
        signal_cls.model_validate.return_value = mock_signal

        mock_proposal = MagicMock()
        mock_proposal.model_dump.return_value = {"pair": "BTC/USD"}

        state = {"signal_payload": {"pair": "BTC/USD"}}  # no agent_id

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mock_proposal,
        ) as mock_d2p:
            result = await strategist_node(state, strategist=strategist, signal_cls=signal_cls)

        assert result["decision_type"] == "PROPOSE"
        mock_d2p.assert_called_once()
        _, kwargs = mock_d2p.call_args
        assert kwargs.get("agent_id") == "unknown"


class TestReputationNode:
    @pytest.mark.asyncio
    async def test_returns_tier_with_value(self) -> None:
        rep_engine = AsyncMock()
        tier_mock = MagicMock()
        tier_mock.value = "PROVEN"
        rep_engine.get_tier.return_value = tier_mock

        state = {"agent_id": "agent-1"}
        result = await reputation_node(state, reputation_engine=rep_engine)

        assert result["agent_tier"] == "PROVEN"

    @pytest.mark.asyncio
    async def test_returns_tier_as_string(self) -> None:
        """When tier has no .value, str() fallback is used."""
        rep_engine = AsyncMock()

        class FakeTier:
            def __str__(self) -> str:
                return "UNPROVEN"

        rep_engine.get_tier.return_value = FakeTier()

        state = {"agent_id": "agent-1"}
        result = await reputation_node(state, reputation_engine=rep_engine)

        assert "agent_tier" in result
        assert result["agent_tier"] == "UNPROVEN"

    @pytest.mark.asyncio
    async def test_uses_unknown_when_no_agent_id(self) -> None:
        rep_engine = AsyncMock()
        tier_mock = MagicMock()
        tier_mock.value = "UNPROVEN"
        rep_engine.get_tier.return_value = tier_mock

        result = await reputation_node({}, reputation_engine=rep_engine)

        rep_engine.get_tier.assert_called_once_with("unknown")
        assert result["agent_tier"] == "UNPROVEN"


class TestRiskNode:
    @pytest.mark.asyncio
    async def test_no_proposal_returns_not_approved(self) -> None:
        risk_mgr = AsyncMock()
        queue = AsyncMock()

        state = {"proposal": None}
        result = await risk_node(state, risk_manager=risk_mgr, queue=queue)

        assert result["verdict_approved"] is False
        assert result["verdict"] is None

    @pytest.mark.asyncio
    async def test_approved_verdict_with_model_dump(self) -> None:
        verdict = MagicMock()
        verdict.approved = True
        verdict.model_dump.return_value = {"approved": True}
        risk_mgr = AsyncMock()
        risk_mgr.evaluate.return_value = verdict
        queue = AsyncMock()

        state = {"proposal": {"pair": "BTC/USD"}, "agent_tier": "PROVEN"}
        result = await risk_node(state, risk_manager=risk_mgr, queue=queue)

        assert result["verdict_approved"] is True
        assert result["verdict"] == {"approved": True}

    @pytest.mark.asyncio
    async def test_verdict_as_dict_fallback(self) -> None:
        """Verdict without model_dump or .approved: uses bool() as approval."""

        class FakeVerdict:
            def __bool__(self) -> bool:
                return True

        risk_mgr = AsyncMock()
        risk_mgr.evaluate.return_value = FakeVerdict()
        queue = AsyncMock()

        state = {"proposal": {"pair": "BTC/USD"}}
        result = await risk_node(state, risk_manager=risk_mgr, queue=queue)

        assert result["verdict_approved"] is True


class TestExecuteNode:
    @pytest.mark.asyncio
    async def test_not_approved_skips_execution(self) -> None:
        kraken = AsyncMock()
        state = {"verdict_approved": False}
        result = await execute_node(state, kraken=kraken)

        assert result["execution_result"] is None
        kraken.place_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_approved_places_order(self) -> None:
        kraken = AsyncMock()
        kraken.place_order.return_value = {"order_id": "ord-123", "status": "filled"}

        state = {
            "verdict_approved": True,
            "proposal": {"pair": "BTC/USD", "side": "buy", "position_size_pct": 0.5},
        }
        result = await execute_node(state, kraken=kraken)

        assert result["order_id"] == "ord-123"
        assert result["execution_result"]["status"] == "filled"
        kraken.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_dict_result_wrapped(self) -> None:
        """Non-dict results from place_order are wrapped in a dict."""
        kraken = AsyncMock()
        kraken.place_order.return_value = "some-order-string"

        state = {
            "verdict_approved": True,
            "proposal": {"pair": "BTC/USD", "side": "buy"},  # no position_size_pct
        }
        result = await execute_node(state, kraken=kraken)

        assert result["execution_result"] == {"raw": "some-order-string"}
        assert result["order_id"] is None

    @pytest.mark.asyncio
    async def test_verdict_not_in_state_skips_execution(self) -> None:
        """Missing verdict_approved key treated as falsy."""
        kraken = AsyncMock()
        state: dict = {}
        result = await execute_node(state, kraken=kraken)

        assert result["execution_result"] is None
        kraken.place_order.assert_not_called()


class TestAuditNodes:
    @pytest.mark.asyncio
    async def test_audit_node_records(self) -> None:
        auditor = AsyncMock()
        state = {"correlation_id": "corr-1"}
        result = await audit_node(state, auditor=auditor)

        assert result["audited"] is True
        auditor.record.assert_called_once_with(state)

    @pytest.mark.asyncio
    async def test_audit_node_swallows_errors(self) -> None:
        auditor = AsyncMock()
        auditor.record.side_effect = RuntimeError("boom")
        result = await audit_node({}, auditor=auditor)

        assert result["audited"] is True

    @pytest.mark.asyncio
    async def test_audit_pass_node_records(self) -> None:
        auditor = AsyncMock()
        state = {"correlation_id": "corr-1", "pass_reasoning": "No signal."}
        result = await audit_pass_node(state, auditor=auditor)

        assert result["audited"] is True
        auditor.record_pass.assert_called_once_with(
            correlation_id="corr-1",
            reasoning="No signal.",
        )

    @pytest.mark.asyncio
    async def test_audit_pass_node_swallows_errors(self) -> None:
        auditor = AsyncMock()
        auditor.record_pass.side_effect = RuntimeError("boom")
        result = await audit_pass_node({}, auditor=auditor)

        assert result["audited"] is True

    @pytest.mark.asyncio
    async def test_audit_pass_node_default_values(self) -> None:
        """Missing state keys use 'unknown' and '' defaults."""
        auditor = AsyncMock()
        result = await audit_pass_node({}, auditor=auditor)

        auditor.record_pass.assert_called_once_with(
            correlation_id="unknown",
            reasoning="",
        )
        assert result["audited"] is True
