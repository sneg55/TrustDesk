"""Orchestrator-specific types."""

from __future__ import annotations

from enum import Enum


class NodeResult(str, Enum):
    """Possible outcomes from graph node execution."""

    CONTINUE = "continue"
    PASS_DECISION = "pass"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
