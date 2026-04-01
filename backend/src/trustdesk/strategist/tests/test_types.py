"""Tests for strategist decision types."""

from __future__ import annotations

import pytest

from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


class TestPassDecision:
    """PassDecision validation."""

    def test_valid_pass_decision(self) -> None:
        decision = PassDecision(decision=DecisionType.PASS, reasoning="market unclear")
        assert decision.decision == DecisionType.PASS

    def test_invalid_decision_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="PassDecision must have decision=PASS"):
            PassDecision(decision=DecisionType.PROPOSE, reasoning="invalid")
