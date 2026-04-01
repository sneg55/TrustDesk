"""Orchestrator-specific types."""

from __future__ import annotations

from enum import StrEnum


class NodeResult(StrEnum):
    """Possible outcomes from graph node execution."""

    CONTINUE = "continue"
    PASS_DECISION = "pass"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
