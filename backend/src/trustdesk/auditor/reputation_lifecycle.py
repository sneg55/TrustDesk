"""Reputation lifecycle: score computation and three-stage feedback building."""

from __future__ import annotations

from trustdesk.auditor.constants import (
    SCORE_BREAKEVEN,
    SCORE_MAX,
    SCORE_MIN,
    SCORE_PNL_MULTIPLIER,
    TAG_TRADE_CLOSE,
    TAG_TRADE_OPEN,
    TAG_TRADE_UPDATE,
)
from trustdesk.auditor.types import FeedbackStage, ReputationEntry


def compute_score(pnl_pct: float) -> int:
    """Compute reputation score from PnL percentage.

    Formula: score = min(100, max(0, 50 + (pnl_pct * 20)))
    Losses map to 0-49, breakeven = 50, profits map to 51-100.
    """
    raw = SCORE_BREAKEVEN + (pnl_pct * SCORE_PNL_MULTIPLIER)
    return min(SCORE_MAX, max(SCORE_MIN, int(raw)))


def build_trade_open_feedback(
    *,
    skill: str,
    entry_price: float,
    size_pct: float,
    regime: str,
    risk_verdict: str,
) -> ReputationEntry:
    """Stage 1: Build TRADE_OPENED reputation entry.

    Score is always SCORE_BREAKEVEN (50) at open since PnL is zero.
    """
    return ReputationEntry(
        feedback_type=FeedbackStage.TRADE_OPENED,
        score=SCORE_BREAKEVEN,
        tag=TAG_TRADE_OPEN,
        skill=skill,
        evidence_uri="",  # Filled by auditor after IPFS upload
        context={
            "entry_price": entry_price,
            "size_pct": size_pct,
            "regime": regime,
            "risk_verdict": risk_verdict,
        },
    )


def build_trade_update_feedback(
    *,
    skill: str,
    unrealized_pnl_pct: float,
    time_in_trade: str,
    stop_moved_to_breakeven: bool,
) -> ReputationEntry:
    """Stage 2: Build TRADE_UPDATE reputation entry.

    Score computed from unrealized PnL.
    """
    return ReputationEntry(
        feedback_type=FeedbackStage.TRADE_UPDATE,
        score=compute_score(unrealized_pnl_pct),
        tag=TAG_TRADE_UPDATE,
        skill=skill,
        evidence_uri="",
        context={
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "time_in_trade": time_in_trade,
            "stop_moved_to_breakeven": stop_moved_to_breakeven,
        },
    )


def build_trade_close_feedback(
    *,
    skill: str,
    entry_price: float,
    exit_price: float,
    realized_pnl_pct: float,
    exit_reason: str,
) -> ReputationEntry:
    """Stage 3: Build TRADE_CLOSED reputation entry.

    Score computed from realized PnL.
    """
    return ReputationEntry(
        feedback_type=FeedbackStage.TRADE_CLOSED,
        score=compute_score(realized_pnl_pct),
        tag=TAG_TRADE_CLOSE,
        skill=skill,
        evidence_uri="",
        context={
            "entry_price": entry_price,
            "exit_price": exit_price,
            "realized_pnl_pct": realized_pnl_pct,
            "exit_reason": exit_reason,
        },
    )
