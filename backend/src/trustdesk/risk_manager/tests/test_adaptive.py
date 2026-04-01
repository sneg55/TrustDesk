# backend/src/trustdesk/risk_manager/tests/test_adaptive.py
"""Tests for adaptive parameter adjustments and drawdown defense."""

from trustdesk.reputation.types import TierLimits
from trustdesk.risk_manager.adaptive import (
    apply_adaptive_adjustments,
    get_drawdown_level,
)
from trustdesk.risk_manager.types import DrawdownLevel, PortfolioState


def _portfolio(**overrides: object) -> PortfolioState:
    defaults = dict(
        open_positions=1,
        total_exposure_pct=10.0,
        daily_realized_loss_pct=1.0,
        current_drawdown_pct=2.0,
        consecutive_losses=0,
        open_pairs=["BTC/USD"],
        last_trade_timestamps={},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)  # type: ignore[arg-type]


class TestDrawdownLevel:
    def test_normal(self) -> None:
        assert get_drawdown_level(2.0) == DrawdownLevel.NORMAL

    def test_caution(self) -> None:
        assert get_drawdown_level(4.0) == DrawdownLevel.CAUTION

    def test_restricted(self) -> None:
        assert get_drawdown_level(6.0) == DrawdownLevel.RESTRICTED

    def test_halt(self) -> None:
        assert get_drawdown_level(10.0) == DrawdownLevel.HALT

    def test_full_cash(self) -> None:
        assert get_drawdown_level(15.0) == DrawdownLevel.FULL_CASH

    def test_boundary_at_3(self) -> None:
        assert get_drawdown_level(3.0) == DrawdownLevel.NORMAL
        assert get_drawdown_level(3.01) == DrawdownLevel.CAUTION


class TestAdaptiveAdjustments:
    def test_normal_no_changes(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio()
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.max_position_pct == 7.0
        assert params.no_new_trades is False
        assert params.full_cash is False

    def test_consecutive_losses_tightens(self) -> None:
        limits = TierLimits(
            capital_usd=1000,
            max_position_pct=10.0,
            max_trades=5,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(consecutive_losses=3)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.max_position_pct == 7.0
        assert params.min_alignment == "STRONG"

    def test_daily_drawdown_above_3_pct(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(daily_realized_loss_pct=3.5)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.min_alignment == "STRONG"
        assert params.reject_overrides is True

    def test_caution_drawdown_level(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=4.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.min_alignment == "STRONG"
        assert params.max_position_pct == 7.0

    def test_restricted_drawdown_level(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=6.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.btc_only is True
        assert params.max_open_positions == 1
        assert params.min_alignment == "STRONG"

    def test_halt_drawdown_level(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=10.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.no_new_trades is True

    def test_full_cash(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=15.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.full_cash is True

    def test_volatile_regime_halves_soft_limits(self) -> None:
        limits = TierLimits(
            capital_usd=1000,
            max_position_pct=10.0,
            max_trades=5,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio()
        params = apply_adaptive_adjustments(limits, portfolio, regime="VOLATILE")
        assert params.max_position_pct == 5.0
        assert params.max_open_positions == 2
