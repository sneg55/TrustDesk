# backend/src/trustdesk/risk_manager/hard_checks.py
"""Deterministic hard checks -- pure functions, no side effects."""
from __future__ import annotations

from trustdesk.risk_manager.types import CheckResult, PortfolioState, RiskParameters

_Outcome = tuple[CheckResult, str]


def check_position_size(
    position_size_pct: float, params: RiskParameters
) -> _Outcome:
    """Position size must be <= tier max."""
    if position_size_pct > params.max_position_pct:
        return (
            CheckResult.FAIL,
            f"Position {position_size_pct}% exceeds max {params.max_position_pct}%",
        )
    return CheckResult.PASS, ""


def check_total_exposure(
    new_position_pct: float,
    portfolio: PortfolioState,
    params: RiskParameters,
) -> _Outcome:
    """Total open exposure must be <= 40% of allocated capital."""
    projected = portfolio.total_exposure_pct + new_position_pct
    if projected > params.max_exposure_pct:
        return (
            CheckResult.FAIL,
            f"Projected exposure {projected:.1f}% exceeds max {params.max_exposure_pct}%",
        )
    return CheckResult.PASS, ""


def check_daily_loss(
    portfolio: PortfolioState, params: RiskParameters
) -> _Outcome:
    """Daily realized loss must be <= tier max."""
    if portfolio.daily_realized_loss_pct > params.max_daily_loss_pct:
        return (
            CheckResult.FAIL,
            f"Daily loss {portfolio.daily_realized_loss_pct:.1f}% exceeds max {params.max_daily_loss_pct}%",
        )
    return CheckResult.PASS, ""


def check_max_open_positions(
    portfolio: PortfolioState, params: RiskParameters
) -> _Outcome:
    """Open positions must be < tier max (new trade would exceed)."""
    if portfolio.open_positions >= params.max_open_positions:
        return (
            CheckResult.FAIL,
            f"Already at {portfolio.open_positions} positions (max {params.max_open_positions})",
        )
    return CheckResult.PASS, ""


def check_min_trade_interval(
    pair: str,
    current_timestamp: int,
    portfolio: PortfolioState,
    params: RiskParameters,
) -> _Outcome:
    """Min time between trades on same pair: 30 minutes."""
    last_ts = portfolio.last_trade_timestamps.get(pair)
    if last_ts is None:
        return CheckResult.PASS, ""
    elapsed = current_timestamp - last_ts
    if elapsed < params.min_trade_interval_seconds:
        remaining = params.min_trade_interval_seconds - elapsed
        return (
            CheckResult.FAIL,
            f"Must wait {remaining}s more before trading {pair}",
        )
    return CheckResult.PASS, ""


def run_all_hard_checks(
    position_size_pct: float,
    pair: str,
    current_timestamp: int,
    portfolio: PortfolioState,
    params: RiskParameters,
) -> tuple[dict[str, CheckResult], dict[str, str]]:
    """Run all hard checks. Returns (results, reasons) dicts."""
    results: dict[str, CheckResult] = {}
    reasons: dict[str, str] = {}

    # Adaptive blockers first
    if params.full_cash:
        results["full_cash"] = CheckResult.FAIL
        reasons["full_cash"] = "Full cash mode active -- no trades allowed"
    if params.no_new_trades:
        results["no_new_trades"] = CheckResult.FAIL
        reasons["no_new_trades"] = "No new trades -- manage existing only"
    if params.btc_only and "BTC" not in pair.upper():
        results["btc_only"] = CheckResult.FAIL
        reasons["btc_only"] = f"BTC-only mode: {pair} rejected"
    elif params.btc_only:
        results["btc_only"] = CheckResult.PASS
        reasons["btc_only"] = ""

    checks = [
        ("position_size", check_position_size(position_size_pct, params)),
        ("total_exposure", check_total_exposure(position_size_pct, portfolio, params)),
        ("daily_loss", check_daily_loss(portfolio, params)),
        ("max_open_positions", check_max_open_positions(portfolio, params)),
        ("min_trade_interval", check_min_trade_interval(pair, current_timestamp, portfolio, params)),
    ]

    for name, (result, reason) in checks:
        results[name] = result
        reasons[name] = reason

    return results, reasons
