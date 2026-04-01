# backend/src/trustdesk/risk_manager/adaptive.py
"""Adaptive parameter adjustments and drawdown defense."""
from __future__ import annotations

from typing import TYPE_CHECKING

from trustdesk.risk_manager.constants import (
    CONSECUTIVE_LOSS_THRESHOLD,
    DAILY_DRAWDOWN_ADAPTIVE_PCT,
    DRAWDOWN_CAUTION_PCT,
    DRAWDOWN_FULL_CASH_PCT,
    DRAWDOWN_HALT_PCT,
    DRAWDOWN_RESTRICTED_PCT,
    MAX_TOTAL_EXPOSURE_PCT,
    MIN_TRADE_INTERVAL_SECONDS,
)
from trustdesk.risk_manager.types import DrawdownLevel, PortfolioState, RiskParameters

if TYPE_CHECKING:
    from trustdesk.reputation.types import TierLimits


def get_drawdown_level(drawdown_pct: float) -> DrawdownLevel:
    """Map drawdown percentage to defense level."""
    if drawdown_pct > DRAWDOWN_FULL_CASH_PCT:
        return DrawdownLevel.FULL_CASH
    if drawdown_pct > DRAWDOWN_HALT_PCT:
        return DrawdownLevel.HALT
    if drawdown_pct > DRAWDOWN_RESTRICTED_PCT:
        return DrawdownLevel.RESTRICTED
    if drawdown_pct > DRAWDOWN_CAUTION_PCT:
        return DrawdownLevel.CAUTION
    return DrawdownLevel.NORMAL


def apply_adaptive_adjustments(
    tier_limits: TierLimits,
    portfolio: PortfolioState,
    regime: str,
) -> RiskParameters:
    """Build effective risk parameters from tier limits + conditions."""
    max_pos = tier_limits.max_position_pct
    max_exposure = MAX_TOTAL_EXPOSURE_PCT
    max_daily = tier_limits.max_daily_loss_pct
    max_open = tier_limits.max_trades
    min_interval = MIN_TRADE_INTERVAL_SECONDS
    min_alignment = "MODERATE"
    reject_overrides = False
    btc_only = False
    no_new_trades = False
    full_cash = False

    # --- Adaptive: consecutive losses ---
    if portfolio.consecutive_losses >= CONSECUTIVE_LOSS_THRESHOLD:
        max_pos = min(max_pos, 7.0)
        min_alignment = "STRONG"

    # --- Adaptive: daily drawdown ---
    if portfolio.daily_realized_loss_pct > DAILY_DRAWDOWN_ADAPTIVE_PCT:
        min_alignment = "STRONG"
        reject_overrides = True

    # --- Adaptive: regime ---
    if regime == "VOLATILE":
        max_pos = max_pos / 2.0
        max_open = max(1, max_open // 2)

    # --- Drawdown defense ---
    dd_level = get_drawdown_level(portfolio.current_drawdown_pct)

    if dd_level == DrawdownLevel.CAUTION:
        min_alignment = "STRONG"
        max_pos = min(max_pos, 7.0)
    elif dd_level == DrawdownLevel.RESTRICTED:
        btc_only = True
        max_open = 1
        min_alignment = "STRONG"
    elif dd_level == DrawdownLevel.HALT:
        no_new_trades = True
    elif dd_level == DrawdownLevel.FULL_CASH:
        full_cash = True

    return RiskParameters(
        max_position_pct=max_pos,
        max_exposure_pct=max_exposure,
        max_daily_loss_pct=max_daily,
        max_open_positions=max_open,
        min_trade_interval_seconds=min_interval,
        min_alignment=min_alignment,
        reject_overrides=reject_overrides,
        btc_only=btc_only,
        no_new_trades=no_new_trades,
        full_cash=full_cash,
    )
