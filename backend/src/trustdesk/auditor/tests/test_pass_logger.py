"""Tests for rate-limited PASS logging."""

from __future__ import annotations

from trustdesk.auditor.constants import PASS_RATE_LIMIT_SECONDS, PASS_SCORE
from trustdesk.auditor.pass_logger import PassLogger
from trustdesk.auditor.types import FeedbackStage, PassSummary


class TestPassLogger:
    """PASS logger: 1 on-chain entry per hour per regime."""

    def setup_method(self) -> None:
        self.logger = PassLogger()

    def test_first_pass_for_regime_is_allowed(self) -> None:
        allowed, summary = self.logger.record_pass(
            regime="TRENDING_UP",
            decision="cycle_42_approved",
        )
        assert allowed is True
        assert summary is not None
        assert summary.regime == "TRENDING_UP"
        assert summary.cycle_count == 1

    def test_second_pass_within_hour_is_batched(self) -> None:
        self.logger.record_pass(regime="TRENDING_UP", decision="cycle_42")
        allowed, summary = self.logger.record_pass(
            regime="TRENDING_UP",
            decision="cycle_43",
        )
        assert allowed is False
        assert summary is None

    def test_pass_after_hour_is_allowed(self) -> None:
        self.logger.record_pass(regime="TRENDING_UP", decision="cycle_42")

        # Simulate time passing beyond rate limit
        regime_key = "TRENDING_UP"
        self.logger._last_post_time[regime_key] -= PASS_RATE_LIMIT_SECONDS + 1

        allowed, summary = self.logger.record_pass(
            regime="TRENDING_UP",
            decision="cycle_99",
        )
        assert allowed is True
        assert summary is not None
        assert summary.cycle_count >= 1

    def test_different_regimes_are_independent(self) -> None:
        allowed1, _ = self.logger.record_pass(
            regime="TRENDING_UP",
            decision="cycle_1",
        )
        allowed2, _ = self.logger.record_pass(
            regime="RANGING",
            decision="cycle_2",
        )
        assert allowed1 is True
        assert allowed2 is True

    def test_regime_transition_always_allowed(self) -> None:
        self.logger.record_pass(regime="TRENDING_UP", decision="cycle_1")
        allowed, summary = self.logger.record_regime_transition(
            from_regime="TRENDING_UP",
            to_regime="RANGING",
        )
        assert allowed is True
        assert summary is not None

    def test_build_pass_feedback_score_is_55(self) -> None:
        feedback = self.logger.build_pass_feedback(
            summary=PassSummary(
                regime="TRENDING_UP",
                cycle_count=5,
                start_time=1000.0,
                end_time=4600.0,
                decisions=["c1", "c2", "c3", "c4", "c5"],
            ),
        )
        assert feedback.score == PASS_SCORE
        assert feedback.feedback_type == FeedbackStage.PASS
        assert feedback.tag == "pass_summary"

    def test_pending_decisions_accumulated(self) -> None:
        self.logger.record_pass(regime="TRENDING_UP", decision="c1")
        self.logger.record_pass(regime="TRENDING_UP", decision="c2")
        self.logger.record_pass(regime="TRENDING_UP", decision="c3")
        pending = self.logger.get_pending_decisions("TRENDING_UP")
        # c1 was posted, c2 and c3 are pending
        assert len(pending) == 2

    def test_flush_clears_pending(self) -> None:
        self.logger.record_pass(regime="TRENDING_UP", decision="c1")
        self.logger.record_pass(regime="TRENDING_UP", decision="c2")
        self.logger.flush_pending("TRENDING_UP")
        pending = self.logger.get_pending_decisions("TRENDING_UP")
        assert len(pending) == 0
