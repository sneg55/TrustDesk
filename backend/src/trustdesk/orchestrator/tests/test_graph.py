"""Tests for the orchestrator LangGraph graph.

All modules are mocked. These tests verify the graph flow, not individual modules.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.orchestrator.graph import _route_after_strategist, build_graph
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


def _build_mocks(
    *,
    decision: str = "PROPOSE",
    approved: bool = True,
) -> dict:
    """Build a full set of mocks for the graph."""
    signal = MagicMock()
    signal.model_dump.return_value = {"pair": "BTC/USD", "alignment_score": 0.9}
    signal.regime.value = "TRENDING_UP"

    engine = AsyncMock()
    engine.generate.return_value = signal

    if decision == "PASS":
        eval_result = PassDecision(
            decision=DecisionType.PASS, reasoning="No signal."
        )
    else:
        eval_result = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )

    strategist = AsyncMock()
    strategist.evaluate.return_value = eval_result

    signal_cls = MagicMock()
    signal_cls.model_validate.return_value = signal

    tier_mock = MagicMock()
    tier_mock.value = "PROVEN"
    reputation_engine = AsyncMock()
    reputation_engine.get_tier.return_value = tier_mock

    verdict = MagicMock()
    verdict.approved = approved
    verdict.model_dump.return_value = {"approved": approved}
    risk_manager = AsyncMock()
    risk_manager.evaluate.return_value = verdict

    queue = AsyncMock()

    kraken = AsyncMock()
    kraken.place_order.return_value = {"order_id": "ord-1", "status": "filled"}

    auditor = AsyncMock()

    # For decision_to_proposal mock
    proposal_mock = MagicMock()
    proposal_mock.model_dump.return_value = {
        "pair": "BTC/USD",
        "side": "buy",
        "position_size_pct": 0.8,
    }

    return {
        "engine": engine,
        "strategist": strategist,
        "signal_cls": signal_cls,
        "reputation_engine": reputation_engine,
        "risk_manager": risk_manager,
        "queue": queue,
        "kraken": kraken,
        "auditor": auditor,
        "proposal_mock": proposal_mock,
    }


class TestRouteAfterStrategist:
    def test_pass_routes_to_audit_pass(self) -> None:
        from trustdesk.orchestrator.constants import NODE_AUDIT_PASS
        state = {"decision_type": "PASS"}
        assert _route_after_strategist(state) == NODE_AUDIT_PASS

    def test_propose_routes_to_reputation(self) -> None:
        from trustdesk.orchestrator.constants import NODE_REPUTATION
        state = {"decision_type": "PROPOSE"}
        assert _route_after_strategist(state) == NODE_REPUTATION

    def test_missing_decision_routes_to_reputation(self) -> None:
        from trustdesk.orchestrator.constants import NODE_REPUTATION
        state: dict = {}
        assert _route_after_strategist(state) == NODE_REPUTATION


class TestGraphProposePath:
    @pytest.mark.asyncio
    async def test_full_propose_approve_execute_flow(self) -> None:
        mocks = _build_mocks(decision="PROPOSE", approved=True)

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mocks["proposal_mock"],
        ):
            graph = build_graph(
                engine=mocks["engine"],
                strategist=mocks["strategist"],
                signal_cls=mocks["signal_cls"],
                reputation_engine=mocks["reputation_engine"],
                risk_manager=mocks["risk_manager"],
                queue=mocks["queue"],
                kraken=mocks["kraken"],
                auditor=mocks["auditor"],
            )
            result = await graph.ainvoke({
                "correlation_id": "test-corr",
                "agent_id": "agent-1",
            })

        assert result["decision_type"] == "PROPOSE"
        assert result["verdict_approved"] is True
        assert result["order_id"] == "ord-1"
        assert result["audited"] is True
        mocks["kraken"].place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_rejected_no_execution(self) -> None:
        mocks = _build_mocks(decision="PROPOSE", approved=False)

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mocks["proposal_mock"],
        ):
            graph = build_graph(
                engine=mocks["engine"],
                strategist=mocks["strategist"],
                signal_cls=mocks["signal_cls"],
                reputation_engine=mocks["reputation_engine"],
                risk_manager=mocks["risk_manager"],
                queue=mocks["queue"],
                kraken=mocks["kraken"],
                auditor=mocks["auditor"],
            )
            result = await graph.ainvoke({
                "correlation_id": "test-corr",
                "agent_id": "agent-1",
            })

        assert result["verdict_approved"] is False
        assert result["execution_result"] is None
        assert result["audited"] is True
        mocks["kraken"].place_order.assert_not_called()


class TestGraphPassPath:
    @pytest.mark.asyncio
    async def test_pass_skips_risk_and_execution(self) -> None:
        mocks = _build_mocks(decision="PASS")

        graph = build_graph(
            engine=mocks["engine"],
            strategist=mocks["strategist"],
            signal_cls=mocks["signal_cls"],
            reputation_engine=mocks["reputation_engine"],
            risk_manager=mocks["risk_manager"],
            queue=mocks["queue"],
            kraken=mocks["kraken"],
            auditor=mocks["auditor"],
        )
        result = await graph.ainvoke({
            "correlation_id": "test-corr",
            "agent_id": "agent-1",
        })

        assert result["decision_type"] == "PASS"
        assert result["audited"] is True
        mocks["reputation_engine"].get_tier.assert_not_called()
        mocks["risk_manager"].evaluate.assert_not_called()
        mocks["kraken"].place_order.assert_not_called()
        mocks["auditor"].record_pass.assert_called_once()
