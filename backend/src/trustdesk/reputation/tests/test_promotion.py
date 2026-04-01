# backend/src/trustdesk/reputation/tests/test_promotion.py
"""Tests for promotion and demotion logic."""
import pytest

from trustdesk.reputation.constants import COOLDOWN_TRADES_REQUIRED
from trustdesk.reputation.promotion import (
    check_demotion,
    check_promotion,
    is_in_cooldown,
)
from trustdesk.reputation.tiers import TierName
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, PromotionResult


def _make_feedback(
    kind: FeedbackKind = FeedbackKind.TRADE_CLOSE,
    score: int = 70,
    pnl_usd: float = 10.0,
    timestamp: int = 1000,
) -> FeedbackRecord:
    return FeedbackRecord(
        kind=kind,
        score=score,
        pnl_usd=pnl_usd,
        timestamp=timestamp,
        metadata={},
    )


class TestCheckPromotion:
    def test_unproven_not_enough_trades(self) -> None:
        history = [_make_feedback() for _ in range(10)]
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is False

    def test_unproven_to_established(self) -> None:
        history = [_make_feedback(pnl_usd=5.0) for _ in range(25)]
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is True
        assert result.new_tier == "ESTABLISHED"

    def test_unproven_to_established_negative_pnl(self) -> None:
        history = [_make_feedback(pnl_usd=-1.0) for _ in range(25)]
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is False
        assert "PnL" in result.reason or "pnl" in result.reason.lower()

    def test_established_to_trusted(self) -> None:
        # 55 trades, 65% equity rising, max DD 8%
        history = []
        for i in range(55):
            pnl = 10.0 if i % 100 < 65 else -3.0
            history.append(_make_feedback(pnl_usd=pnl, timestamp=1000 + i))
        result = check_promotion(TierName.ESTABLISHED, history)
        assert result.changed is True
        assert result.new_tier == "TRUSTED"

    def test_established_not_enough_trades_for_trusted(self) -> None:
        # Only 30 trades from ESTABLISHED -- needs 50
        history = [_make_feedback(pnl_usd=5.0) for _ in range(30)]
        result = check_promotion(TierName.ESTABLISHED, history)
        assert result.changed is False
        assert str(50) in result.reason or "trades" in result.reason.lower()

    def test_trusted_cannot_promote(self) -> None:
        history = [_make_feedback() for _ in range(100)]
        result = check_promotion(TierName.TRUSTED, history)
        assert result.changed is False

    def test_established_to_trusted_fails_equity_rising(self) -> None:
        # 55 trades but only 50% equity rising (< 60% threshold)
        history = []
        for i in range(55):
            # Even indices positive, odd negative -> 50% equity rising
            pnl = 5.0 if i % 2 == 0 else -1.0
            history.append(_make_feedback(pnl_usd=pnl, timestamp=1000 + i))
        result = check_promotion(TierName.ESTABLISHED, history)
        assert result.changed is False


class TestCheckDemotion:
    def test_no_demotion_on_good_history(self) -> None:
        history = [_make_feedback(pnl_usd=5.0) for _ in range(10)]
        result = check_demotion(
            TierName.ESTABLISHED, history, current_drawdown_pct=2.0, daily_loss_pct=1.0
        )
        assert result.changed is False

    def test_demotion_on_max_drawdown_exceeded(self) -> None:
        history = [_make_feedback() for _ in range(10)]
        result = check_demotion(
            TierName.ESTABLISHED,
            history,
            current_drawdown_pct=16.0,
            daily_loss_pct=0.0,
        )
        assert result.changed is True
        assert result.new_tier == "UNPROVEN"

    def test_demotion_on_consecutive_losses(self) -> None:
        history = [_make_feedback(pnl_usd=-5.0) for _ in range(5)]
        result = check_demotion(
            TierName.TRUSTED, history, current_drawdown_pct=2.0, daily_loss_pct=1.0
        )
        assert result.changed is True
        assert result.new_tier == "ESTABLISHED"

    def test_demotion_on_daily_loss_breach(self) -> None:
        history = [_make_feedback() for _ in range(10)]
        result = check_demotion(
            TierName.ESTABLISHED,
            history,
            current_drawdown_pct=2.0,
            daily_loss_pct=6.0,
        )
        assert result.changed is True

    def test_no_demotion_below_unproven(self) -> None:
        history = [_make_feedback(pnl_usd=-5.0) for _ in range(5)]
        result = check_demotion(
            TierName.UNPROVEN, history, current_drawdown_pct=2.0, daily_loss_pct=1.0
        )
        assert result.changed is False


class TestInternalHelpers:
    def test_equity_rising_pct_empty_history(self) -> None:
        """_equity_rising_pct returns 0.0 when no TRADE_CLOSE records."""
        from trustdesk.reputation.promotion import _equity_rising_pct
        result = _equity_rising_pct([])
        assert result == 0.0

    def test_max_drawdown_empty_history(self) -> None:
        """_max_drawdown_from_history returns 0.0 when no TRADE_CLOSE records."""
        from trustdesk.reputation.promotion import _max_drawdown_from_history
        result = _max_drawdown_from_history([])
        assert result == 0.0

    def test_max_drawdown_only_losses(self) -> None:
        """_max_drawdown_from_history when equity never exceeds peak=0."""
        from trustdesk.reputation.promotion import _max_drawdown_from_history
        history = [_make_feedback(pnl_usd=-5.0, timestamp=1000 + i) for i in range(3)]
        result = _max_drawdown_from_history(history)
        assert result == 0.0

    def test_unproven_to_established_drawdown_exceeds_15pct(self) -> None:
        """Promotion blocked when max drawdown > 15%."""
        history = [
            _make_feedback(pnl_usd=100.0, timestamp=1000),
            _make_feedback(pnl_usd=-20.0, timestamp=1001),
        ]
        history.extend([_make_feedback(pnl_usd=1.0, timestamp=1002 + i) for i in range(20)])
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is False
        assert "drawdown" in result.reason.lower() or "15%" in result.reason

    def test_established_to_trusted_drawdown_exceeds_10pct(self) -> None:
        """Promotion to TRUSTED blocked when max drawdown > 10%."""
        # 55 trades with high equity rising but a large drawdown spike
        history = [
            _make_feedback(pnl_usd=100.0, timestamp=1000),
            _make_feedback(pnl_usd=-15.0, timestamp=1001),
        ]
        history.extend([_make_feedback(pnl_usd=5.0, timestamp=1002 + i) for i in range(55)])
        result = check_promotion(TierName.ESTABLISHED, history)
        assert result.changed is False
        assert "drawdown" in result.reason.lower() or "10%" in result.reason


class TestCooldown:
    def test_in_cooldown_not_enough_trades(self) -> None:
        last_demotion_ts = 5000
        history = [
            _make_feedback(timestamp=5001 + i)
            for i in range(COOLDOWN_TRADES_REQUIRED - 1)
        ]
        assert is_in_cooldown(history, last_demotion_ts) is True

    def test_cooldown_cleared(self) -> None:
        last_demotion_ts = 5000
        history = [
            _make_feedback(timestamp=5001 + i)
            for i in range(COOLDOWN_TRADES_REQUIRED)
        ]
        assert is_in_cooldown(history, last_demotion_ts) is False

    def test_no_cooldown_without_demotion(self) -> None:
        assert is_in_cooldown([], None) is False
