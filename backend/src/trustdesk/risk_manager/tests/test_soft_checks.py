# backend/src/trustdesk/risk_manager/tests/test_soft_checks.py
"""Tests for LLM-evaluated soft checks."""
import pytest

from trustdesk.risk_manager.soft_checks import (
    build_soft_check_prompt,
    parse_llm_response,
    run_soft_checks,
)
from trustdesk.risk_manager.types import CheckResult


class TestParseLLMResponse:
    def test_all_pass(self) -> None:
        raw = {
            "correlation": "PASS",
            "regime_alignment": "PASS",
            "drawdown_headroom": "PASS",
            "invalidation_plausibility": "PASS",
            "alignment_score_calibration": "PASS",
            "override_scrutiny": "PASS",
        }
        results, details = parse_llm_response(raw)
        assert all(r == CheckResult.PASS for r in results.values())
        assert all(d == "" for d in details.values())

    def test_fail_with_reason(self) -> None:
        raw = {
            "correlation": "FAIL: BTC and ETH are 90% correlated",
            "regime_alignment": "PASS",
            "drawdown_headroom": "PASS",
            "invalidation_plausibility": "PASS",
            "alignment_score_calibration": "PASS",
            "override_scrutiny": "PASS",
        }
        results, details = parse_llm_response(raw)
        assert results["correlation"] == CheckResult.FAIL
        assert "90% correlated" in details["correlation"]

    def test_missing_check_treated_as_fail(self) -> None:
        raw = {"correlation": "PASS"}
        results, details = parse_llm_response(raw)
        assert results["regime_alignment"] == CheckResult.FAIL
        assert "missing" in details["regime_alignment"].lower()

    def test_unexpected_value_treated_as_fail(self) -> None:
        raw = {
            "correlation": "MAYBE",
            "regime_alignment": "PASS",
            "drawdown_headroom": "PASS",
            "invalidation_plausibility": "PASS",
            "alignment_score_calibration": "PASS",
            "override_scrutiny": "PASS",
        }
        results, details = parse_llm_response(raw)
        assert results["correlation"] == CheckResult.FAIL


class TestBuildPrompt:
    def test_returns_nonempty_string(self) -> None:
        prompt = build_soft_check_prompt(
            proposal={"pair": "BTC/USD", "size_pct": 5.0},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "correlation" in prompt.lower()


class TestRunSoftChecks:
    @pytest.mark.asyncio
    async def test_with_passing_evaluator(self) -> None:
        async def mock_eval(proposal: dict, portfolio: dict, parameters: dict) -> dict[str, str]:
            return {
                "correlation": "PASS",
                "regime_alignment": "PASS",
                "drawdown_headroom": "PASS",
                "invalidation_plausibility": "PASS",
                "alignment_score_calibration": "PASS",
                "override_scrutiny": "PASS",
            }

        results, details = await run_soft_checks(
            evaluator=mock_eval,
            proposal={"pair": "BTC/USD"},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert all(r == CheckResult.PASS for r in results.values())

    @pytest.mark.asyncio
    async def test_with_failing_evaluator(self) -> None:
        async def mock_eval(proposal: dict, portfolio: dict, parameters: dict) -> dict[str, str]:
            return {
                "correlation": "FAIL: too correlated",
                "regime_alignment": "PASS",
                "drawdown_headroom": "PASS",
                "invalidation_plausibility": "PASS",
                "alignment_score_calibration": "PASS",
                "override_scrutiny": "PASS",
            }

        results, details = await run_soft_checks(
            evaluator=mock_eval,
            proposal={"pair": "BTC/USD"},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert results["correlation"] == CheckResult.FAIL
        assert "too correlated" in details["correlation"]

    @pytest.mark.asyncio
    async def test_evaluator_exception_all_fail(self) -> None:
        async def mock_eval(proposal: dict, portfolio: dict, parameters: dict) -> dict[str, str]:
            raise RuntimeError("API unavailable")

        results, details = await run_soft_checks(
            evaluator=mock_eval,
            proposal={"pair": "BTC/USD"},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert all(r == CheckResult.FAIL for r in results.values())
