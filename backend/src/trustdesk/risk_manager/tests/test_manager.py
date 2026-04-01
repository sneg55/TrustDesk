# backend/src/trustdesk/risk_manager/tests/test_manager.py
"""Tests for the risk manager orchestrator."""
import pytest

from trustdesk.reputation.engine import ReputationEngine
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord
from trustdesk.risk_manager.circuit_breaker import CircuitBreaker
from trustdesk.risk_manager.manager import RiskManager
from trustdesk.risk_manager.types import PortfolioState, VerdictStatus


def _close(pnl: float, ts: int) -> FeedbackRecord:
    return FeedbackRecord(
        kind=FeedbackKind.TRADE_CLOSE,
        score=70,
        pnl_usd=pnl,
        timestamp=ts,
        metadata={},
    )


def _portfolio(**overrides: object) -> PortfolioState:
    defaults = dict(
        open_positions=0,
        total_exposure_pct=0.0,
        daily_realized_loss_pct=0.0,
        current_drawdown_pct=0.0,
        consecutive_losses=0,
        open_pairs=[],
        last_trade_timestamps={},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)  # type: ignore[arg-type]


async def _pass_evaluator(
    proposal: dict, portfolio: dict, parameters: dict
) -> dict[str, str]:
    return {
        "correlation": "PASS",
        "regime_alignment": "PASS",
        "drawdown_headroom": "PASS",
        "invalidation_plausibility": "PASS",
        "alignment_score_calibration": "PASS",
        "override_scrutiny": "PASS",
    }


async def _fail_evaluator(
    proposal: dict, portfolio: dict, parameters: dict
) -> dict[str, str]:
    return {
        "correlation": "FAIL: 95% correlated",
        "regime_alignment": "PASS",
        "drawdown_headroom": "PASS",
        "invalidation_plausibility": "PASS",
        "alignment_score_calibration": "PASS",
        "override_scrutiny": "PASS",
    }


class TestRiskManager:
    @pytest.mark.asyncio
    async def test_approve_clean_proposal(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_oversized_position(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 5.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        # Unproven tier: max 3%
        assert verdict.status == VerdictStatus.REJECTED
        assert any("position" in r.lower() for r in verdict.hard_reasons.values() if r)

    @pytest.mark.asyncio
    async def test_reject_on_soft_check_fail(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_fail_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.REJECTED

    @pytest.mark.asyncio
    async def test_hard_only_when_circuit_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, reset_timeout_s=9999)
        cb.record_failure()  # Opens circuit

        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=cb,
            llm_evaluator=_fail_evaluator,  # Should not be called
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.APPROVED_HARD_ONLY
        assert verdict.soft_checks_note == "SKIPPED_LLM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_established_agent_higher_limits(self) -> None:
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 5.0},
            portfolio=_portfolio(),
            feedback_history=history,
            regime="TRENDING",
            current_timestamp=5000,
        )
        # Established tier: max 7%, so 5% should pass
        assert verdict.status == VerdictStatus.APPROVED

    @pytest.mark.asyncio
    async def test_verdict_contains_tier_info(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.tier == "UNPROVEN"
        assert verdict.effective_limits is not None


class TestRiskManagerDrawdownDefense:
    @pytest.mark.asyncio
    async def test_halt_blocks_new_trades(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 1.0},
            portfolio=_portfolio(current_drawdown_pct=10.0),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.REJECTED

    @pytest.mark.asyncio
    async def test_full_cash_blocks_everything(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 1.0},
            portfolio=_portfolio(current_drawdown_pct=15.0),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.REJECTED
