# backend/src/trustdesk/reputation/promotion.py
"""Promotion, demotion, and cooldown logic."""
from __future__ import annotations

from trustdesk.reputation.constants import (
    COOLDOWN_TRADES_REQUIRED,
    DEMOTION_CONSECUTIVE_LOSSES,
    ESTABLISHED_MAX_DD_PCT,
    ESTABLISHED_MIN_PNL,
    ESTABLISHED_MIN_TRADES,
    TRUSTED_EQUITY_RISING_PCT,
    TRUSTED_MAX_DD_PCT,
    TRUSTED_MIN_TRADES,
)
from trustdesk.reputation.tiers import TIER_DEFINITIONS, TierName
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, PromotionResult


def _count_closed_trades(history: list[FeedbackRecord]) -> int:
    return sum(1 for f in history if f.kind == FeedbackKind.TRADE_CLOSE)


def _total_pnl(history: list[FeedbackRecord]) -> float:
    return sum(f.pnl_usd for f in history if f.kind == FeedbackKind.TRADE_CLOSE)


def _equity_rising_pct(history: list[FeedbackRecord]) -> float:
    closes = [f for f in history if f.kind == FeedbackKind.TRADE_CLOSE]
    if not closes:
        return 0.0
    rising = sum(1 for f in closes if f.pnl_usd > 0)
    return (rising / len(closes)) * 100.0


def _max_drawdown_from_history(history: list[FeedbackRecord]) -> float:
    closes = sorted(
        (f for f in history if f.kind == FeedbackKind.TRADE_CLOSE),
        key=lambda f: f.timestamp,
    )
    if not closes:
        return 0.0
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for f in closes:
        equity += f.pnl_usd
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = ((peak - equity) / peak) * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _no_change(tier: TierName, reason: str) -> PromotionResult:
    return PromotionResult(
        changed=False, old_tier=tier.name, new_tier=tier.name, reason=reason
    )


def check_promotion(
    current_tier: TierName, history: list[FeedbackRecord]
) -> PromotionResult:
    """Check if the agent qualifies for promotion."""
    if current_tier == TierName.TRUSTED:
        return _no_change(current_tier, "Already at highest tier")

    trade_count = _count_closed_trades(history)

    if current_tier == TierName.UNPROVEN:
        if trade_count < ESTABLISHED_MIN_TRADES:
            return _no_change(current_tier, f"Need {ESTABLISHED_MIN_TRADES} trades, have {trade_count}")
        if _total_pnl(history) <= ESTABLISHED_MIN_PNL:
            return _no_change(current_tier, "Total PnL must be positive")
        if _max_drawdown_from_history(history) > ESTABLISHED_MAX_DD_PCT:
            return _no_change(current_tier, "Max drawdown exceeds 15%")
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=TierName.ESTABLISHED.name,
            reason="Met ESTABLISHED criteria",
        )

    # ESTABLISHED -> TRUSTED
    if trade_count < TRUSTED_MIN_TRADES:
        return _no_change(current_tier, f"Need {TRUSTED_MIN_TRADES} trades, have {trade_count}")
    if _equity_rising_pct(history) < TRUSTED_EQUITY_RISING_PCT:
        return _no_change(current_tier, "Equity rising percentage too low")
    if _max_drawdown_from_history(history) > TRUSTED_MAX_DD_PCT:
        return _no_change(current_tier, "Max drawdown exceeds 10%")
    return PromotionResult(
        changed=True,
        old_tier=current_tier.name,
        new_tier=TierName.TRUSTED.name,
        reason="Met TRUSTED criteria",
    )


def check_demotion(
    current_tier: TierName,
    history: list[FeedbackRecord],
    current_drawdown_pct: float,
    daily_loss_pct: float,
) -> PromotionResult:
    """Check if the agent should be demoted."""
    if current_tier == TierName.UNPROVEN:
        return _no_change(current_tier, "Already at lowest tier")

    tier_limits = TIER_DEFINITIONS[current_tier]

    # Check max drawdown exceeded (15% hard limit)
    if current_drawdown_pct > ESTABLISHED_MAX_DD_PCT:
        new_tier = TierName(current_tier.value - 1)
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=new_tier.name,
            reason=f"Max drawdown {current_drawdown_pct:.1f}% exceeds 15%",
        )

    # Check consecutive losses
    closes = [f for f in history if f.kind == FeedbackKind.TRADE_CLOSE]
    recent = closes[-DEMOTION_CONSECUTIVE_LOSSES:]
    if len(recent) == DEMOTION_CONSECUTIVE_LOSSES and all(
        f.pnl_usd < 0 for f in recent
    ):
        new_tier = TierName(current_tier.value - 1)
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=new_tier.name,
            reason=f"{DEMOTION_CONSECUTIVE_LOSSES} consecutive losses",
        )

    # Check daily loss limit
    if daily_loss_pct > tier_limits.max_daily_loss_pct:
        new_tier = TierName(current_tier.value - 1)
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=new_tier.name,
            reason=f"Daily loss {daily_loss_pct:.1f}% exceeds {tier_limits.max_daily_loss_pct}%",
        )

    return _no_change(current_tier, "No demotion triggers")


def is_in_cooldown(
    history: list[FeedbackRecord],
    last_demotion_timestamp: int | None,
) -> bool:
    """Check if agent is still in cooldown after demotion."""
    if last_demotion_timestamp is None:
        return False
    trades_since = sum(
        1
        for f in history
        if f.kind == FeedbackKind.TRADE_CLOSE
        and f.timestamp > last_demotion_timestamp
    )
    return trades_since < COOLDOWN_TRADES_REQUIRED
