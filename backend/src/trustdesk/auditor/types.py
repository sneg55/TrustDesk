"""Auditor type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeedbackStage(str, Enum):
    """Three-stage reputation lifecycle."""

    TRADE_OPENED = "TRADE_OPENED"
    TRADE_UPDATE = "TRADE_UPDATE"
    TRADE_CLOSED = "TRADE_CLOSED"
    PASS = "PASS"


@dataclass(frozen=True)
class ReputationEntry:
    """Single reputation feedback entry for on-chain posting."""

    feedback_type: FeedbackStage
    score: int
    tag: str
    skill: str
    evidence_uri: str
    context: dict[str, Any]


@dataclass(frozen=True)
class TradeOpenContext:
    """Context for TRADE_OPENED feedback."""

    entry_price: float
    size_pct: float
    regime: str
    risk_verdict: str


@dataclass(frozen=True)
class TradeUpdateContext:
    """Context for TRADE_UPDATE feedback."""

    unrealized_pnl_pct: float
    time_in_trade: str
    stop_moved_to_breakeven: bool


@dataclass(frozen=True)
class TradeCloseContext:
    """Context for TRADE_CLOSED feedback."""

    entry_price: float
    exit_price: float
    realized_pnl_pct: float
    exit_reason: str


@dataclass
class PassSummary:
    """Hourly PASS summary for a regime."""

    regime: str
    cycle_count: int
    start_time: float
    end_time: float
    decisions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TrustPathResult:
    """Result of the dual-path trust write."""

    proposal_cid: str
    verdict_cid: str
    validation_request_tx: str
    validation_response_tx: str
    success: bool
    error: str | None = None


@dataclass
class RetryTask:
    """A failed write queued for retry."""

    task_id: str
    payload: dict[str, Any]
    attempt: int = 0
    next_retry_at: float = 0.0
