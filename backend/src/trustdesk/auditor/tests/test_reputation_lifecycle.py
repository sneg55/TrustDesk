"""Tests for reputation lifecycle score computation and feedback building."""

from __future__ import annotations

import pytest

from trustdesk.auditor.constants import (
    FEEDBACK_TRADE_CLOSED,
    FEEDBACK_TRADE_OPENED,
    FEEDBACK_TRADE_UPDATE,
    SCORE_BREAKEVEN,
    SCORE_MAX,
    SCORE_MIN,
)
from trustdesk.auditor.reputation_lifecycle import (
    build_trade_close_feedback,
    build_trade_open_feedback,
    build_trade_update_feedback,
    compute_score,
)
from trustdesk.auditor.types import FeedbackStage


class TestComputeScore:
    """Score = min(100, max(0, 50 + (pnl_pct * 20)))."""

    def test_breakeven_returns_50(self) -> None:
        assert compute_score(0.0) == SCORE_BREAKEVEN

    def test_positive_pnl_above_50(self) -> None:
        assert compute_score(1.0) == 70

    def test_negative_pnl_below_50(self) -> None:
        assert compute_score(-1.0) == 30

    def test_large_profit_capped_at_100(self) -> None:
        assert compute_score(5.0) == SCORE_MAX

    def test_large_loss_capped_at_0(self) -> None:
        assert compute_score(-5.0) == SCORE_MIN

    def test_small_profit(self) -> None:
        assert compute_score(0.5) == 60

    def test_small_loss(self) -> None:
        assert compute_score(-0.5) == 40

    def test_exact_cap_boundary_upper(self) -> None:
        # 50 + (2.5 * 20) = 100
        assert compute_score(2.5) == SCORE_MAX

    def test_exact_cap_boundary_lower(self) -> None:
        # 50 + (-2.5 * 20) = 0
        assert compute_score(-2.5) == SCORE_MIN


class TestBuildTradeOpenFeedback:
    """Stage 1: TRADE_OPENED."""

    def test_returns_correct_type(self) -> None:
        entry = build_trade_open_feedback(
            skill="BTC/USD",
            entry_price=68200.0,
            size_pct=5.5,
            regime="TRENDING_UP",
            risk_verdict="APPROVED_WITH_MODIFICATION",
        )
        assert entry.feedback_type == FeedbackStage.TRADE_OPENED
        assert entry.score == SCORE_BREAKEVEN
        assert entry.tag == "trade_open"
        assert entry.skill == "BTC/USD"

    def test_context_contains_all_fields(self) -> None:
        entry = build_trade_open_feedback(
            skill="ETH/USD",
            entry_price=3500.0,
            size_pct=2.0,
            regime="RANGING",
            risk_verdict="APPROVED",
        )
        ctx = entry.context
        assert ctx["entry_price"] == 3500.0
        assert ctx["size_pct"] == 2.0
        assert ctx["regime"] == "RANGING"
        assert ctx["risk_verdict"] == "APPROVED"


class TestBuildTradeUpdateFeedback:
    """Stage 2: TRADE_UPDATE."""

    def test_score_computed_from_unrealized_pnl(self) -> None:
        entry = build_trade_update_feedback(
            skill="BTC/USD",
            unrealized_pnl_pct=1.2,
            time_in_trade="2h15m",
            stop_moved_to_breakeven=True,
        )
        assert entry.feedback_type == FeedbackStage.TRADE_UPDATE
        # 50 + (1.2 * 20) = 74
        assert entry.score == 74
        assert entry.tag == "trade_update"

    def test_negative_unrealized_pnl(self) -> None:
        entry = build_trade_update_feedback(
            skill="ETH/USD",
            unrealized_pnl_pct=-1.5,
            time_in_trade="45m",
            stop_moved_to_breakeven=False,
        )
        # 50 + (-1.5 * 20) = 20
        assert entry.score == 20


class TestBuildTradeCloseFeedback:
    """Stage 3: TRADE_CLOSED."""

    def test_profitable_trade(self) -> None:
        entry = build_trade_close_feedback(
            skill="BTC/USD",
            entry_price=68200.0,
            exit_price=69010.0,
            realized_pnl_pct=1.19,
            exit_reason="TP1_HIT",
        )
        assert entry.feedback_type == FeedbackStage.TRADE_CLOSED
        # 50 + (1.19 * 20) = 73.8 -> 73
        assert entry.score == 73
        assert entry.tag == "trade_close"
        assert entry.context["exit_reason"] == "TP1_HIT"

    def test_losing_trade(self) -> None:
        entry = build_trade_close_feedback(
            skill="BTC/USD",
            entry_price=68200.0,
            exit_price=67500.0,
            realized_pnl_pct=-1.03,
            exit_reason="STOP_LOSS",
        )
        # 50 + (-1.03 * 20) = 29.4 -> 29
        assert entry.score == 29
