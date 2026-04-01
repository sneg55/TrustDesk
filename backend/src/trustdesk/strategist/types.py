"""Strategist decision types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DecisionType(str, Enum):
    """Whether the strategist proposes a trade or passes."""

    PROPOSE = "PROPOSE"
    PASS = "PASS"


@dataclass(frozen=True)
class StrategistDecision:
    """A PROPOSE decision with reasoning and parameters."""

    decision: DecisionType
    reasoning: str
    pair: str
    side: str  # "buy" or "sell"
    confidence: float
    position_size_pct: float
    override_justification: str | None = None


@dataclass(frozen=True)
class PassDecision:
    """A PASS decision with reasoning."""

    decision: DecisionType
    reasoning: str

    def __post_init__(self) -> None:
        if self.decision != DecisionType.PASS:
            msg = "PassDecision must have decision=PASS"
            raise ValueError(msg)
