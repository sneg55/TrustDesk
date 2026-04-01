# backend/src/trustdesk/risk_manager/soft_checks.py
"""LLM-evaluated soft checks."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from trustdesk.risk_manager.constants import ALL_SOFT_CHECKS
from trustdesk.risk_manager.types import CheckResult

logger = logging.getLogger(__name__)

SoftEvaluator = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any]],
    Awaitable[dict[str, str]],
]


def parse_llm_response(
    raw: dict[str, str],
) -> tuple[dict[str, CheckResult], dict[str, str]]:
    """Parse LLM response into check results and detail strings."""
    results: dict[str, CheckResult] = {}
    details: dict[str, str] = {}

    for check_name in ALL_SOFT_CHECKS:
        value = raw.get(check_name)

        if value is None:
            results[check_name] = CheckResult.FAIL
            details[check_name] = "Missing from LLM response"
            continue

        if value == "PASS":
            results[check_name] = CheckResult.PASS
            details[check_name] = ""
        elif value.startswith("FAIL"):
            results[check_name] = CheckResult.FAIL
            # Extract reason after "FAIL: "
            reason = value[len("FAIL"):].lstrip(": ").strip()
            details[check_name] = reason if reason else "No reason given"
        else:
            results[check_name] = CheckResult.FAIL
            details[check_name] = f"Unexpected response: {value}"

    return results, details


def build_soft_check_prompt(
    proposal: dict[str, Any],
    portfolio: dict[str, Any],
    parameters: dict[str, Any],
) -> str:
    """Build the prompt for LLM soft check evaluation."""
    return f"""You are a risk manager evaluating a trade proposal.

## Proposal
{_fmt(proposal)}

## Current Portfolio
{_fmt(portfolio)}

## Risk Parameters
{_fmt(parameters)}

## Checks to evaluate
For each check, respond with EXACTLY "PASS" or "FAIL: <reason>".

1. **correlation**: Is the correlated exposure above 60%? Check if the
   proposed pair is heavily correlated with existing open positions.
2. **regime_alignment**: Does the proposal match the current market regime?
3. **drawdown_headroom**: Is there enough room before hitting -15% max DD?
4. **invalidation_plausibility**: Is the stated invalidation level
   monitorable and realistic?
5. **alignment_score_calibration**: Does the alignment score match the
   aggressiveness of the trade?
6. **override_scrutiny**: If an override is present, is the reasoning sound?
   If no override, respond PASS.

Respond as JSON with keys: correlation, regime_alignment, drawdown_headroom,
invalidation_plausibility, alignment_score_calibration, override_scrutiny."""


def _fmt(d: dict[str, Any]) -> str:
    return "\n".join(f"  {k}: {v}" for k, v in d.items())


async def run_soft_checks(
    evaluator: SoftEvaluator,
    proposal: dict[str, Any],
    portfolio: dict[str, Any],
    parameters: dict[str, Any],
) -> tuple[dict[str, CheckResult], dict[str, str]]:
    """Run soft checks via LLM evaluator. Handles exceptions gracefully."""
    try:
        raw = await evaluator(proposal, portfolio, parameters)
        return parse_llm_response(raw)
    except Exception:
        logger.exception("Soft check evaluator failed")
        results = {name: CheckResult.FAIL for name in ALL_SOFT_CHECKS}
        details = {name: "Evaluator error" for name in ALL_SOFT_CHECKS}
        return results, details
