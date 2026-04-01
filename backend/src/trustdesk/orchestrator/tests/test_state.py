"""Tests for orchestrator state schema and types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from trustdesk.orchestrator.types import NodeResult

if TYPE_CHECKING:
    from trustdesk.orchestrator.state import PipelineState


class TestPipelineState:
    def test_empty_state_is_valid(self) -> None:
        state: PipelineState = {}
        assert state == {}

    def test_partial_state_is_valid(self) -> None:
        state: PipelineState = {
            "correlation_id": "corr-123",
            "agent_id": "agent-1",
        }
        assert state["correlation_id"] == "corr-123"

    def test_full_state_is_valid(self) -> None:
        state: PipelineState = {
            "correlation_id": "corr-123",
            "agent_id": "agent-1",
            "signal_payload": {"pair": "BTC/USD"},
            "regime": "TRENDING_UP",
            "decision_type": "PROPOSE",
            "proposal": {"pair": "BTC/USD", "side": "buy"},
            "pass_reasoning": None,
            "agent_tier": "PROVEN",
            "verdict": {"approved": True},
            "verdict_approved": True,
            "execution_result": {"order_id": "ord-1"},
            "order_id": "ord-1",
            "audited": True,
            "error": None,
        }
        assert state["verdict_approved"] is True
        assert state["order_id"] == "ord-1"


class TestNodeResult:
    def test_all_values_are_strings(self) -> None:
        for member in NodeResult:
            assert isinstance(member.value, str)

    def test_continue_value(self) -> None:
        assert NodeResult.CONTINUE == "continue"

    def test_pass_decision_value(self) -> None:
        assert NodeResult.PASS_DECISION == "pass"

    def test_approved_value(self) -> None:
        assert NodeResult.APPROVED == "approved"

    def test_rejected_value(self) -> None:
        assert NodeResult.REJECTED == "rejected"

    def test_executed_value(self) -> None:
        assert NodeResult.EXECUTED == "executed"

    def test_failed_value(self) -> None:
        assert NodeResult.FAILED == "failed"
