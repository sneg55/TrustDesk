# backend/src/trustdesk/risk_manager/manager.py
"""Risk manager -- main evaluation pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from trustdesk.risk_manager.adaptive import apply_adaptive_adjustments
from trustdesk.risk_manager.hard_checks import run_all_hard_checks
from trustdesk.risk_manager.soft_checks import SoftEvaluator, run_soft_checks
from trustdesk.risk_manager.types import (
    CheckResult,
    PortfolioState,
    RiskParameters,
    VerdictStatus,
)

if TYPE_CHECKING:
    from trustdesk.reputation.engine import ReputationEngine
    from trustdesk.reputation.types import FeedbackRecord
    from trustdesk.risk_manager.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Verdict:
    """Final risk verdict for a trade proposal."""

    status: VerdictStatus
    tier: str
    effective_limits: RiskParameters
    hard_results: dict[str, CheckResult]
    hard_reasons: dict[str, str]
    soft_results: dict[str, CheckResult]
    soft_details: dict[str, str]
    soft_checks_note: str


class RiskManager:
    """Orchestrates reputation lookup, hard checks, soft checks."""

    def __init__(
        self,
        reputation_engine: ReputationEngine,
        circuit_breaker: CircuitBreaker,
        llm_evaluator: SoftEvaluator,
    ) -> None:
        self._reputation = reputation_engine
        self._circuit = circuit_breaker
        self._llm = llm_evaluator

    async def evaluate(
        self,
        proposal: dict[str, Any],
        portfolio: PortfolioState,
        feedback_history: list[FeedbackRecord],
        regime: str,
        current_timestamp: int,
    ) -> Verdict:
        """Evaluate a trade proposal through the full pipeline."""
        # 1. Get tier from reputation engine
        rep = self._reputation.evaluate(
            feedback_history,
            current_drawdown_pct=portfolio.current_drawdown_pct,
            daily_loss_pct=portfolio.daily_realized_loss_pct,
        )

        # 2. Build effective parameters
        params = apply_adaptive_adjustments(rep.limits, portfolio, regime)

        # 3. Run hard checks
        pair = proposal.get("pair", "UNKNOWN")
        size_pct = float(proposal.get("size_pct", 0.0))

        hard_results, hard_reasons = run_all_hard_checks(
            position_size_pct=size_pct,
            pair=pair,
            current_timestamp=current_timestamp,
            portfolio=portfolio,
            params=params,
        )

        hard_failed = any(r == CheckResult.FAIL for r in hard_results.values())

        # 4. Short-circuit on hard failure
        if hard_failed:
            return Verdict(
                status=VerdictStatus.REJECTED,
                tier=rep.tier.name,
                effective_limits=params,
                hard_results=hard_results,
                hard_reasons=hard_reasons,
                soft_results={},
                soft_details={},
                soft_checks_note="SKIPPED_HARD_FAILED",
            )

        # 5. Circuit breaker check
        if not self._circuit.is_available:
            return Verdict(
                status=VerdictStatus.APPROVED_HARD_ONLY,
                tier=rep.tier.name,
                effective_limits=params,
                hard_results=hard_results,
                hard_reasons=hard_reasons,
                soft_results={},
                soft_details={},
                soft_checks_note="SKIPPED_LLM_UNAVAILABLE",
            )

        # 6. Run soft checks (run_soft_checks handles exceptions internally)
        soft_results, soft_details = await run_soft_checks(
            evaluator=self._llm,
            proposal=proposal,
            portfolio=_portfolio_to_dict(portfolio),
            parameters=_params_to_dict(params),
        )
        self._circuit.record_success()

        soft_failed = any(r == CheckResult.FAIL for r in soft_results.values())

        return Verdict(
            status=VerdictStatus.REJECTED if soft_failed else VerdictStatus.APPROVED,
            tier=rep.tier.name,
            effective_limits=params,
            hard_results=hard_results,
            hard_reasons=hard_reasons,
            soft_results=soft_results,
            soft_details=soft_details,
            soft_checks_note="",
        )


def _portfolio_to_dict(p: PortfolioState) -> dict[str, Any]:
    return {
        "open_positions": p.open_positions,
        "total_exposure_pct": p.total_exposure_pct,
        "daily_realized_loss_pct": p.daily_realized_loss_pct,
        "current_drawdown_pct": p.current_drawdown_pct,
        "consecutive_losses": p.consecutive_losses,
        "open_pairs": p.open_pairs,
    }


def _params_to_dict(p: RiskParameters) -> dict[str, Any]:
    return {
        "max_position_pct": p.max_position_pct,
        "max_exposure_pct": p.max_exposure_pct,
        "max_daily_loss_pct": p.max_daily_loss_pct,
        "max_open_positions": p.max_open_positions,
        "min_alignment": p.min_alignment,
        "btc_only": p.btc_only,
        "no_new_trades": p.no_new_trades,
    }
