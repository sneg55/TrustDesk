# backend/src/trustdesk/risk_manager/types.py
"""Internal types for the risk manager."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class CheckResult(StrEnum):
    """Result of a single risk check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class VerdictStatus(StrEnum):
    """Overall verdict status."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPROVED_HARD_ONLY = "APPROVED_HARD_ONLY"


class DrawdownLevel(StrEnum):
    """Current drawdown defense level."""

    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    RESTRICTED = "RESTRICTED"
    HALT = "HALT"
    FULL_CASH = "FULL_CASH"


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Current state of the agent's portfolio."""

    open_positions: int
    total_exposure_pct: float
    daily_realized_loss_pct: float
    current_drawdown_pct: float
    consecutive_losses: int
    open_pairs: list[str]
    last_trade_timestamps: dict[str, int]


@dataclass(frozen=True, slots=True)
class RiskParameters:
    """Effective risk parameters after adaptive adjustments."""

    max_position_pct: float
    max_exposure_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    min_trade_interval_seconds: int
    min_alignment: str
    reject_overrides: bool
    btc_only: bool
    no_new_trades: bool
    full_cash: bool


@dataclass(slots=True)
class CheckReport:
    """Report from running all checks."""

    hard_checks: dict[str, CheckResult] = field(default_factory=dict)
    soft_checks: dict[str, CheckResult] = field(default_factory=dict)
    soft_details: dict[str, str] = field(default_factory=dict)
    hard_reasons: dict[str, str] = field(default_factory=dict)


class LLMEvaluator(Protocol):
    """Protocol for the LLM-based soft check evaluator."""

    async def evaluate_soft_checks(
        self,
        proposal: dict,
        portfolio: dict,
        parameters: dict,
    ) -> dict[str, str]:
        """Return dict mapping check_name -> 'PASS' or 'FAIL: reason'."""
        ...
