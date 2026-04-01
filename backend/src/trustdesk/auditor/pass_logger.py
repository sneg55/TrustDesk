"""Rate-limited PASS decision logger.

Posts at most 1 on-chain PASS entry per hour per regime.
Individual cycles are batched into hourly summaries.
Regime transitions are logged immediately regardless of rate limit.
"""

from __future__ import annotations

import time

from trustdesk.auditor.constants import (
    PASS_RATE_LIMIT_SECONDS,
    PASS_SCORE,
    TAG_PASS,
)
from trustdesk.auditor.types import FeedbackStage, PassSummary, ReputationEntry


class PassLogger:
    """Manages rate-limited PASS logging with per-regime tracking."""

    def __init__(self) -> None:
        self._last_post_time: dict[str, float] = {}
        self._pending_decisions: dict[str, list[str]] = {}
        self._batch_start_time: dict[str, float] = {}

    def record_pass(
        self,
        *,
        regime: str,
        decision: str,
    ) -> tuple[bool, PassSummary | None]:
        """Record a PASS decision. Returns (should_post, summary_or_none).

        First call for a regime posts immediately.
        Subsequent calls within the hour are batched.
        """
        now = time.monotonic()

        if regime not in self._last_post_time:
            # First pass for this regime: post immediately
            self._last_post_time[regime] = now
            self._pending_decisions[regime] = []
            self._batch_start_time[regime] = now
            summary = PassSummary(
                regime=regime,
                cycle_count=1,
                start_time=now,
                end_time=now,
                decisions=[decision],
            )
            return True, summary

        elapsed = now - self._last_post_time[regime]

        if elapsed >= PASS_RATE_LIMIT_SECONDS:
            # Hour elapsed: flush pending + this one
            pending = self._pending_decisions.get(regime, [])
            all_decisions = [*pending, decision]
            start = self._batch_start_time.get(regime, now)
            summary = PassSummary(
                regime=regime,
                cycle_count=len(all_decisions),
                start_time=start,
                end_time=now,
                decisions=all_decisions,
            )
            self._last_post_time[regime] = now
            self._pending_decisions[regime] = []
            self._batch_start_time[regime] = now
            return True, summary

        # Within the hour: batch it
        self._pending_decisions[regime].append(decision)
        return False, None

    def record_regime_transition(
        self,
        *,
        from_regime: str,
        to_regime: str,
    ) -> tuple[bool, PassSummary | None]:
        """Log regime transition immediately, bypassing rate limit."""
        now = time.monotonic()
        summary = PassSummary(
            regime=f"{from_regime}->{to_regime}",
            cycle_count=1,
            start_time=now,
            end_time=now,
            decisions=[f"regime_transition:{from_regime}->{to_regime}"],
        )
        # Reset the old regime tracking
        self._last_post_time.pop(from_regime, None)
        self._pending_decisions.pop(from_regime, None)
        self._batch_start_time.pop(from_regime, None)
        return True, summary

    def build_pass_feedback(self, *, summary: PassSummary) -> ReputationEntry:
        """Build a ReputationEntry for a PASS summary."""
        return ReputationEntry(
            feedback_type=FeedbackStage.PASS,
            score=PASS_SCORE,
            tag=TAG_PASS,
            skill="desk",
            evidence_uri="",
            context={
                "regime": summary.regime,
                "cycle_count": summary.cycle_count,
                "decisions": summary.decisions,
            },
        )

    def get_pending_decisions(self, regime: str) -> list[str]:
        """Return pending (unbatched) decisions for a regime."""
        return list(self._pending_decisions.get(regime, []))

    def flush_pending(self, regime: str) -> None:
        """Clear pending decisions for a regime."""
        self._pending_decisions.pop(regime, None)
