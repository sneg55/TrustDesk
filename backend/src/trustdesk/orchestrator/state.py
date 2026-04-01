"""LangGraph state schema for the orchestrator pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    """State carried through the orchestrator graph.

    All fields are optional (total=False) because they are
    populated progressively as nodes execute.
    """

    # Identifiers
    correlation_id: str
    agent_id: str

    # Signal phase
    signal_payload: dict[str, Any]
    regime: str

    # Strategist phase
    decision_type: str  # "PROPOSE" or "PASS"
    proposal: dict[str, Any] | None
    pass_reasoning: str | None

    # Reputation phase
    agent_tier: str | None

    # Risk phase
    verdict: dict[str, Any] | None
    verdict_approved: bool

    # Execution phase
    execution_result: dict[str, Any] | None
    order_id: str | None

    # Audit
    audited: bool

    # Error tracking
    error: str | None
