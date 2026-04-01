"""Graph node functions for the orchestrator pipeline.

Each node is a thin wrapper: takes PipelineState, calls the appropriate
module, and returns state updates. Business logic stays in the modules.
"""

from __future__ import annotations

import logging
from typing import Any

from trustdesk.orchestrator.state import PipelineState
from trustdesk.strategist.strategist import decision_to_proposal
from trustdesk.strategist.types import DecisionType

logger = logging.getLogger(__name__)


async def signal_engine_node(
    state: PipelineState,
    *,
    engine: Any,
) -> dict[str, Any]:
    """Run the signal engine and populate signal_payload."""
    signal = await engine.generate()
    return {
        "signal_payload": signal.model_dump(mode="json"),
        "regime": signal.regime.value if hasattr(signal.regime, "value") else str(signal.regime),
    }


async def strategist_node(
    state: PipelineState,
    *,
    strategist: Any,
    signal_cls: Any,
) -> dict[str, Any]:
    """Run the strategist on the current signal payload."""
    signal = signal_cls.model_validate(state["signal_payload"])
    decision = await strategist.evaluate(signal)

    if decision.decision == DecisionType.PASS:
        return {
            "decision_type": DecisionType.PASS.value,
            "proposal": None,
            "pass_reasoning": decision.reasoning,
        }

    # Build proposal dict from the StrategistDecision
    proposal = decision_to_proposal(decision, signal, agent_id=state.get("agent_id", "unknown"))
    return {
        "decision_type": DecisionType.PROPOSE.value,
        "proposal": proposal.model_dump(mode="json"),
        "pass_reasoning": None,
    }


async def reputation_node(
    state: PipelineState,
    *,
    reputation_engine: Any,
) -> dict[str, Any]:
    """Look up the agent's reputation tier."""
    agent_id = state.get("agent_id", "unknown")
    tier = await reputation_engine.get_tier(agent_id)
    return {"agent_tier": tier.value if hasattr(tier, "value") else str(tier)}


async def risk_node(
    state: PipelineState,
    *,
    risk_manager: Any,
    queue: Any,  # noqa: ARG001
) -> dict[str, Any]:
    """Send proposal through risk manager, return verdict."""
    proposal = state.get("proposal")
    if proposal is None:
        return {"verdict": None, "verdict_approved": False}

    verdict = await risk_manager.evaluate(proposal, tier=state.get("agent_tier"))
    return {
        "verdict": verdict.model_dump(mode="json") if hasattr(verdict, "model_dump") else verdict,
        "verdict_approved": verdict.approved if hasattr(verdict, "approved") else bool(verdict),
    }


async def execute_node(
    state: PipelineState,
    *,
    kraken: Any,
) -> dict[str, Any]:
    """Execute the trade via Kraken adapter."""
    if not state.get("verdict_approved"):
        return {"execution_result": None, "order_id": None}

    proposal = state["proposal"]
    result = await kraken.place_order(
        pair=proposal["pair"],
        side=proposal["side"],
        size=proposal.get("position_size_pct", 0.5),
    )
    return {
        "execution_result": result if isinstance(result, dict) else {"raw": str(result)},
        "order_id": result.get("order_id") if isinstance(result, dict) else None,
    }


async def audit_node(
    state: PipelineState,
    *,
    auditor: Any,
) -> dict[str, Any]:
    """Trigger the auditor (fire and forget)."""
    try:
        await auditor.record(state)
    except Exception:
        logger.exception("Auditor failed, continuing")
    return {"audited": True}


async def audit_pass_node(
    state: PipelineState,
    *,
    auditor: Any,
) -> dict[str, Any]:
    """Record a PASS decision in the audit trail."""
    try:
        await auditor.record_pass(
            correlation_id=state.get("correlation_id", "unknown"),
            reasoning=state.get("pass_reasoning", ""),
        )
    except Exception:
        logger.exception("Auditor pass recording failed, continuing")
    return {"audited": True}
