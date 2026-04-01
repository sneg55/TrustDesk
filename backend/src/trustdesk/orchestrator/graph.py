"""LangGraph graph definition for the orchestrator pipeline."""

from __future__ import annotations

import functools
from typing import Any

from langgraph.graph import END, StateGraph

from trustdesk.orchestrator.constants import (
    NODE_AUDIT,
    NODE_AUDIT_PASS,
    NODE_EXECUTE,
    NODE_REPUTATION,
    NODE_RISK,
    NODE_SIGNAL,
    NODE_STRATEGIST,
)
from trustdesk.orchestrator.nodes import (
    audit_node,
    audit_pass_node,
    execute_node,
    reputation_node,
    risk_node,
    signal_engine_node,
    strategist_node,
)
from trustdesk.orchestrator.state import PipelineState


def _route_after_strategist(state: PipelineState) -> str:
    """Route based on strategist decision."""
    if state.get("decision_type") == "PASS":
        return NODE_AUDIT_PASS
    return NODE_REPUTATION


def build_graph(
    *,
    engine: Any,
    strategist: Any,
    signal_cls: Any,
    reputation_engine: Any,
    risk_manager: Any,
    queue: Any,
    kraken: Any,
    auditor: Any,
) -> Any:
    """Build and compile the orchestrator pipeline graph.

    Dependencies are injected via functools.partial so node functions
    remain testable in isolation.
    """
    graph = StateGraph(PipelineState)

    # Bind dependencies to node functions
    graph.add_node(
        NODE_SIGNAL,
        functools.partial(signal_engine_node, engine=engine),
    )
    graph.add_node(
        NODE_STRATEGIST,
        functools.partial(strategist_node, strategist=strategist, signal_cls=signal_cls),
    )
    graph.add_node(
        NODE_REPUTATION,
        functools.partial(reputation_node, reputation_engine=reputation_engine),
    )
    graph.add_node(
        NODE_RISK,
        functools.partial(risk_node, risk_manager=risk_manager, queue=queue),
    )
    graph.add_node(
        NODE_EXECUTE,
        functools.partial(execute_node, kraken=kraken),
    )
    graph.add_node(
        NODE_AUDIT,
        functools.partial(audit_node, auditor=auditor),
    )
    graph.add_node(
        NODE_AUDIT_PASS,
        functools.partial(audit_pass_node, auditor=auditor),
    )

    # Edges
    graph.set_entry_point(NODE_SIGNAL)
    graph.add_edge(NODE_SIGNAL, NODE_STRATEGIST)
    graph.add_conditional_edges(
        NODE_STRATEGIST,
        _route_after_strategist,
        {NODE_AUDIT_PASS: NODE_AUDIT_PASS, NODE_REPUTATION: NODE_REPUTATION},
    )
    graph.add_edge(NODE_REPUTATION, NODE_RISK)
    graph.add_edge(NODE_RISK, NODE_EXECUTE)
    graph.add_edge(NODE_EXECUTE, NODE_AUDIT)
    graph.add_edge(NODE_AUDIT, END)
    graph.add_edge(NODE_AUDIT_PASS, END)

    return graph.compile()
