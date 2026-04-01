# backend/src/trustdesk/reputation/engine.py
"""Reputation engine -- computes tier from feedback history."""
from __future__ import annotations

from dataclasses import dataclass

from trustdesk.reputation.constants import DEMOTION_SCORE
from trustdesk.reputation.promotion import check_demotion, check_promotion, is_in_cooldown
from trustdesk.reputation.tiers import TierName, get_tier_limits
from trustdesk.reputation.types import (
    FeedbackKind,
    FeedbackRecord,
    PromotionResult,
    TierLimits,
)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Result of a reputation evaluation."""

    tier: TierName
    limits: TierLimits
    promotion_result: PromotionResult | None
    demotion_result: PromotionResult | None


class ReputationEngine:
    """Pure computation engine: feedback history -> tier + limits."""

    def evaluate(
        self,
        history: list[FeedbackRecord],
        current_drawdown_pct: float,
        daily_loss_pct: float,
    ) -> EvaluationResult:
        """Evaluate an agent's tier based on feedback history."""
        if not history:
            return EvaluationResult(
                tier=TierName.UNPROVEN,
                limits=get_tier_limits(TierName.UNPROVEN),
                promotion_result=None,
                demotion_result=None,
            )

        # Start at UNPROVEN, check if promotions apply
        current_tier = TierName.UNPROVEN

        # Check promotion (iteratively up the tiers)
        promo_result: PromotionResult | None = None
        last_demotion_ts = self._find_last_demotion_ts(history)

        # Check if in cooldown
        if not is_in_cooldown(history, last_demotion_ts):
            # Try to promote through tiers
            while current_tier < TierName.TRUSTED:
                result = check_promotion(current_tier, history)
                if not result.changed:
                    # Only store a "no change" if we haven't promoted yet
                    if promo_result is None:
                        promo_result = result
                    break
                current_tier = TierName[result.new_tier]
                promo_result = result

        # Check demotion
        demo_result = check_demotion(
            current_tier, history, current_drawdown_pct, daily_loss_pct
        )
        if demo_result.changed:
            current_tier = TierName[demo_result.new_tier]

        return EvaluationResult(
            tier=current_tier,
            limits=get_tier_limits(current_tier),
            promotion_result=promo_result,
            demotion_result=demo_result if demo_result.changed else None,
        )

    def _find_last_demotion_ts(
        self, history: list[FeedbackRecord]
    ) -> int | None:
        """Find timestamp of the most recent demotion event."""
        demotions = [
            f
            for f in history
            if f.kind == FeedbackKind.TIER_CHANGE and f.score == DEMOTION_SCORE
        ]
        if not demotions:
            return None
        return max(f.timestamp for f in demotions)
