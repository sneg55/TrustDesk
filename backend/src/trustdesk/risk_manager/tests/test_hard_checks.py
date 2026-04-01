# backend/src/trustdesk/risk_manager/tests/test_hard_checks.py
"""Tests for deterministic hard checks."""
import pytest

from trustdesk.risk_manager.hard_checks import (
    check_daily_loss,
    check_max_open_positions,
    check_min_trade_interval,
    check_position_size,
    check_total_exposure,
    run_all_hard_checks,
)
from trustdesk.risk_manager.types import CheckResult, PortfolioState, RiskParameters


def _default_params(**overrides: object) -> RiskParameters:
    defaults = dict(
        max_position_pct=7.0,
        max_exposure_pct=40.0,
        max_daily_loss_pct=5.0,
        max_open_positions=3,
        min_trade_interval_seconds=1800,
        min_alignment="MODERATE",
        reject_overrides=False,
        btc_only=False,
        no_new_trades=False,
        full_cash=False,
    )
    defaults.update(overrides)
    return RiskParameters(**defaults)  # type: ignore[arg-type]


def _default_portfolio(**overrides: object) -> PortfolioState:
    defaults = dict(
        open_positions=1,
        total_exposure_pct=15.0,
        daily_realized_loss_pct=1.0,
        current_drawdown_pct=2.0,
        consecutive_losses=0,
        open_pairs=["BTC/USD"],
        last_trade_timestamps={"BTC/USD": 1000},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)  # type: ignore[arg-type]


class TestPositionSize:
    def test_within_limit(self) -> None:
        result, reason = check_position_size(5.0, _default_params())
        assert result == CheckResult.PASS

    def test_exceeds_limit(self) -> None:
        result, reason = check_position_size(10.0, _default_params())
        assert result == CheckResult.FAIL
        assert "10.0%" in reason


class TestTotalExposure:
    def test_within_limit(self) -> None:
        result, reason = check_total_exposure(
            5.0, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.PASS

    def test_exceeds_limit(self) -> None:
        portfolio = _default_portfolio(total_exposure_pct=38.0)
        result, reason = check_total_exposure(5.0, portfolio, _default_params())
        assert result == CheckResult.FAIL


class TestDailyLoss:
    def test_within_limit(self) -> None:
        result, reason = check_daily_loss(_default_portfolio(), _default_params())
        assert result == CheckResult.PASS

    def test_exceeds_limit(self) -> None:
        portfolio = _default_portfolio(daily_realized_loss_pct=6.0)
        result, reason = check_daily_loss(portfolio, _default_params())
        assert result == CheckResult.FAIL


class TestMaxOpenPositions:
    def test_within_limit(self) -> None:
        result, reason = check_max_open_positions(_default_portfolio(), _default_params())
        assert result == CheckResult.PASS

    def test_at_limit(self) -> None:
        portfolio = _default_portfolio(open_positions=3)
        result, reason = check_max_open_positions(portfolio, _default_params())
        assert result == CheckResult.FAIL


class TestMinTradeInterval:
    def test_enough_time(self) -> None:
        result, reason = check_min_trade_interval(
            "BTC/USD", 5000, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.PASS

    def test_too_soon(self) -> None:
        result, reason = check_min_trade_interval(
            "BTC/USD", 1500, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.FAIL

    def test_new_pair_always_passes(self) -> None:
        result, reason = check_min_trade_interval(
            "ETH/USD", 1000, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.PASS


class TestRunAllHardChecks:
    def test_all_pass(self) -> None:
        results, reasons = run_all_hard_checks(
            position_size_pct=5.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=_default_params(),
        )
        assert all(r == CheckResult.PASS for r in results.values())

    def test_no_new_trades(self) -> None:
        params = _default_params(no_new_trades=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["no_new_trades"] == CheckResult.FAIL

    def test_full_cash(self) -> None:
        params = _default_params(full_cash=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["full_cash"] == CheckResult.FAIL

    def test_btc_only_rejects_non_btc(self) -> None:
        params = _default_params(btc_only=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["btc_only"] == CheckResult.FAIL

    def test_btc_only_allows_btc(self) -> None:
        params = _default_params(btc_only=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="BTC/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["btc_only"] == CheckResult.PASS
