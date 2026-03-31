"""Tests for ReputationFeedback, TierDefinition schemas, and PositionCallback."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from trustdesk.schemas.callbacks import PositionCallback
from trustdesk.schemas.reputation import ReputationFeedback, TierDefinition


class TestReputationFeedback:
    def _minimal_feedback(self, **overrides) -> dict:
        base = {
            "type": "TRADE_OPENED",
            "score": 10,
            "tag": "entry_quality",
            "skill": "trend_following",
            "evidence_uri": "ipfs://QmABC123",
            "context": {"proposal_id": "prop-001", "pair": "BTC/USD"},
        }
        base.update(overrides)
        return base

    def test_create_minimal_feedback(self) -> None:
        """ReputationFeedback is created with all required fields."""
        fb = ReputationFeedback(**self._minimal_feedback())
        assert fb.type == "TRADE_OPENED"
        assert fb.score == 10
        assert fb.tag == "entry_quality"
        assert fb.skill == "trend_following"
        assert fb.evidence_uri == "ipfs://QmABC123"
        assert fb.context == {"proposal_id": "prop-001", "pair": "BTC/USD"}

    def test_all_feedback_types(self) -> None:
        """All valid type literals are accepted."""
        for fb_type in ("TRADE_OPENED", "TRADE_UPDATE", "TRADE_CLOSED", "PASS_SUMMARY", "RISK_ADJUST"):
            fb = ReputationFeedback(**self._minimal_feedback(type=fb_type))
            assert fb.type == fb_type

    def test_invalid_type_raises(self) -> None:
        """Invalid type literal raises ValidationError."""
        with pytest.raises(ValidationError):
            ReputationFeedback(**self._minimal_feedback(type="TRADE_SKIPPED"))

    def test_negative_score(self) -> None:
        """Negative score is valid (penalties are negative)."""
        fb = ReputationFeedback(**self._minimal_feedback(score=-5))
        assert fb.score == -5

    def test_zero_score(self) -> None:
        """Zero score is valid."""
        fb = ReputationFeedback(**self._minimal_feedback(score=0))
        assert fb.score == 0

    def test_context_accepts_nested_data(self) -> None:
        """context accepts complex nested dict."""
        context = {
            "proposal_id": "prop-001",
            "pnl_pct": 3.5,
            "duration_hours": 12,
            "tags": ["ema_cross", "volume_spike"],
        }
        fb = ReputationFeedback(**self._minimal_feedback(context=context))
        assert fb.context["pnl_pct"] == 3.5
        assert fb.context["tags"] == ["ema_cross", "volume_spike"]

    def test_model_dump_round_trip(self) -> None:
        """ReputationFeedback round-trips through model_dump."""
        original = ReputationFeedback(**self._minimal_feedback())
        reconstructed = ReputationFeedback(**original.model_dump())
        assert reconstructed == original

    def test_model_dump_contains_expected_keys(self) -> None:
        """model_dump includes all expected keys."""
        fb = ReputationFeedback(**self._minimal_feedback())
        dumped = fb.model_dump()
        assert set(dumped.keys()) == {"type", "score", "tag", "skill", "evidence_uri", "context"}

    def test_trade_closed_feedback_with_pnl(self) -> None:
        """Realistic TRADE_CLOSED feedback with pnl data."""
        fb = ReputationFeedback(
            type="TRADE_CLOSED",
            score=25,
            tag="profitable_exit",
            skill="trend_following",
            evidence_uri="ipfs://QmCLOSED",
            context={
                "proposal_id": "prop-042",
                "pair": "ETH/USD",
                "pnl_pct": 4.2,
                "tp_hit": 1,
                "hold_hours": 8,
            },
        )
        assert fb.type == "TRADE_CLOSED"
        assert fb.score == 25
        assert fb.context["pnl_pct"] == 4.2


class TestTierDefinition:
    def _minimal_tier(self, **overrides) -> dict:
        base = {
            "tier": "ESTABLISHED",
            "capital_allocation": 0.10,
            "max_position_pct": 3.0,
            "max_open_trades": 3,
            "max_daily_loss_pct": 5.0,
        }
        base.update(overrides)
        return base

    def test_create_minimal_tier(self) -> None:
        """TierDefinition is created with all required fields."""
        tier_def = TierDefinition(**self._minimal_tier())
        assert tier_def.tier == "ESTABLISHED"
        assert tier_def.capital_allocation == 0.10
        assert tier_def.max_position_pct == 3.0
        assert tier_def.max_open_trades == 3
        assert tier_def.max_daily_loss_pct == 5.0

    def test_all_tier_values(self) -> None:
        """All valid tier literals are accepted."""
        for tier in ("UNPROVEN", "ESTABLISHED", "TRUSTED"):
            tier_def = TierDefinition(**self._minimal_tier(tier=tier))
            assert tier_def.tier == tier

    def test_invalid_tier_raises(self) -> None:
        """Invalid tier literal raises ValidationError."""
        with pytest.raises(ValidationError):
            TierDefinition(**self._minimal_tier(tier="EXPERT"))

    def test_unproven_tier_constraints(self) -> None:
        """UNPROVEN tier typically has conservative constraints."""
        tier_def = TierDefinition(
            tier="UNPROVEN",
            capital_allocation=0.02,
            max_position_pct=1.0,
            max_open_trades=1,
            max_daily_loss_pct=2.0,
        )
        assert tier_def.tier == "UNPROVEN"
        assert tier_def.max_open_trades == 1

    def test_trusted_tier_constraints(self) -> None:
        """TRUSTED tier has more generous constraints."""
        tier_def = TierDefinition(
            tier="TRUSTED",
            capital_allocation=0.25,
            max_position_pct=5.0,
            max_open_trades=5,
            max_daily_loss_pct=10.0,
        )
        assert tier_def.tier == "TRUSTED"
        assert tier_def.capital_allocation == 0.25

    def test_model_dump_round_trip(self) -> None:
        """TierDefinition round-trips through model_dump."""
        original = TierDefinition(**self._minimal_tier())
        reconstructed = TierDefinition(**original.model_dump())
        assert reconstructed == original

    def test_model_dump_contains_expected_keys(self) -> None:
        """model_dump includes all expected keys."""
        tier_def = TierDefinition(**self._minimal_tier())
        dumped = tier_def.model_dump()
        expected_keys = {"tier", "capital_allocation", "max_position_pct", "max_open_trades", "max_daily_loss_pct"}
        assert set(dumped.keys()) == expected_keys


class TestPositionCallback:
    def _minimal_callback(self, **overrides) -> dict:
        base = {
            "event": "FILLED",
            "proposal_id": "prop-001",
            "timestamp": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            "details": {"fill_price": 42050.0, "size": 0.025},
        }
        base.update(overrides)
        return base

    def test_create_minimal_callback(self) -> None:
        """PositionCallback is created with all required fields."""
        cb = PositionCallback(**self._minimal_callback())
        assert cb.event == "FILLED"
        assert cb.proposal_id == "prop-001"
        assert cb.details == {"fill_price": 42050.0, "size": 0.025}

    def test_all_event_values(self) -> None:
        """All valid event literals are accepted."""
        for event in ("FILLED", "PARTIAL_EXIT", "STOP_TRIGGERED", "TIME_EXIT", "INVALIDATION_EXIT", "DEMOTION"):
            cb = PositionCallback(**self._minimal_callback(event=event))
            assert cb.event == event

    def test_invalid_event_raises(self) -> None:
        """Invalid event literal raises ValidationError."""
        with pytest.raises(ValidationError):
            PositionCallback(**self._minimal_callback(event="CANCELLED"))

    def test_timestamp_from_string(self) -> None:
        """timestamp field parses ISO strings."""
        cb = PositionCallback(**self._minimal_callback(timestamp="2024-06-01T12:00:00Z"))
        assert cb.timestamp.year == 2024

    def test_details_accepts_nested_data(self) -> None:
        """details accepts complex nested dict."""
        details = {
            "fill_price": 42050.0,
            "size": 0.025,
            "remaining_size": 0.0,
            "pnl_pct": 3.5,
            "exit_reason": "TP1 hit",
        }
        cb = PositionCallback(**self._minimal_callback(details=details))
        assert cb.details["pnl_pct"] == 3.5

    def test_stop_triggered_callback(self) -> None:
        """Realistic STOP_TRIGGERED callback is valid."""
        cb = PositionCallback(
            event="STOP_TRIGGERED",
            proposal_id="prop-007",
            timestamp=datetime(2024, 1, 16, 14, 30, 0, tzinfo=timezone.utc),
            details={
                "stop_price": 41000.0,
                "fill_price": 40950.0,
                "pnl_pct": -2.4,
                "slippage_pct": 0.12,
            },
        )
        assert cb.event == "STOP_TRIGGERED"
        assert cb.details["pnl_pct"] == -2.4

    def test_demotion_callback(self) -> None:
        """Realistic DEMOTION callback is valid."""
        cb = PositionCallback(
            event="DEMOTION",
            proposal_id="prop-999",
            timestamp=datetime(2024, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
            details={
                "previous_tier": "ESTABLISHED",
                "new_tier": "UNPROVEN",
                "reason": "3 consecutive losses exceeded threshold.",
            },
        )
        assert cb.event == "DEMOTION"
        assert cb.details["previous_tier"] == "ESTABLISHED"

    def test_model_dump_round_trip(self) -> None:
        """PositionCallback round-trips through model_dump."""
        original = PositionCallback(**self._minimal_callback())
        dumped = original.model_dump()
        reconstructed = PositionCallback(**dumped)
        assert reconstructed == original

    def test_model_dump_contains_expected_keys(self) -> None:
        """model_dump includes all expected keys."""
        cb = PositionCallback(**self._minimal_callback())
        dumped = cb.model_dump()
        assert set(dumped.keys()) == {"event", "proposal_id", "timestamp", "details"}
