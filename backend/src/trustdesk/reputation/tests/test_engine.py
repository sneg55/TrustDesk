# backend/src/trustdesk/reputation/tests/test_engine.py
"""Tests for the reputation engine orchestrator."""
import pytest

from trustdesk.reputation.engine import ReputationEngine
from trustdesk.reputation.tiers import TierName
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, TierLimits


def _close(pnl: float, ts: int = 1000) -> FeedbackRecord:
    return FeedbackRecord(
        kind=FeedbackKind.TRADE_CLOSE,
        score=70,
        pnl_usd=pnl,
        timestamp=ts,
        metadata={},
    )


def _tier_change(ts: int, score: int) -> FeedbackRecord:
    return FeedbackRecord(
        kind=FeedbackKind.TIER_CHANGE,
        score=score,
        pnl_usd=0.0,
        timestamp=ts,
        metadata={},
    )


class TestReputationEngine:
    def test_new_agent_is_unproven(self) -> None:
        engine = ReputationEngine()
        result = engine.evaluate([], current_drawdown_pct=0.0, daily_loss_pct=0.0)
        assert result.tier == TierName.UNPROVEN

    def test_returns_tier_limits(self) -> None:
        engine = ReputationEngine()
        result = engine.evaluate([], current_drawdown_pct=0.0, daily_loss_pct=0.0)
        assert result.limits.capital_usd == 100
        assert result.limits.max_position_pct == 3.0

    def test_promotion_after_enough_trades(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.tier == TierName.ESTABLISHED
        assert result.limits.capital_usd == 500

    def test_demotion_on_drawdown(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        result = engine.evaluate(
            history, current_drawdown_pct=20.0, daily_loss_pct=0.0
        )
        # Would be ESTABLISHED by promotion but gets demoted
        assert result.tier == TierName.UNPROVEN

    def test_cooldown_prevents_repromotion(self) -> None:
        engine = ReputationEngine()
        # History: 25 good trades, then demotion event, then 3 trades
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        history.append(_tier_change(ts=2000, score=40))  # demotion
        history.extend([_close(pnl=5.0, ts=2001 + i) for i in range(3)])
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.tier == TierName.UNPROVEN  # cooldown active

    def test_cooldown_clears_after_enough_trades(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        history.append(_tier_change(ts=2000, score=40))  # demotion
        history.extend([_close(pnl=5.0, ts=2001 + i) for i in range(5)])
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        # Cooldown cleared, 30 total closes, PnL > 0 => ESTABLISHED
        assert result.tier == TierName.ESTABLISHED


    def test_promotes_to_trusted_tier(self) -> None:
        engine = ReputationEngine()
        # 60 trades with 70% positive PnL, low DD
        history = []
        for i in range(60):
            pnl = 5.0 if i % 10 < 7 else -1.0
            history.append(_close(pnl=pnl, ts=1000 + i))
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.tier == TierName.TRUSTED
        assert result.limits.capital_usd == 1000

    def test_history_with_no_promotion_stores_no_change_result(self) -> None:
        engine = ReputationEngine()
        # Only 5 trades -- not enough for any promotion
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(5)]
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.tier == TierName.UNPROVEN
        assert result.promotion_result is not None
        assert result.promotion_result.changed is False


class TestEvaluationResult:
    def test_result_has_promotion_info(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.promotion_result is not None
        assert result.promotion_result.changed is True
