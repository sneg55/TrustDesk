"""Strategist: receives SignalPayload, calls LLM, returns StrategistDecision or PassDecision."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from trustdesk.strategist.constants import (
    NO_SIGNAL_THRESHOLD,
    POSITION_SIZE_MULTIPLIER,
    REGIME_TRENDING_DOWN,
    WEAK_THRESHOLD,
)
from trustdesk.strategist.prompts import SYSTEM_PROMPT, build_user_prompt
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision

if TYPE_CHECKING:
    from trustdesk.schemas import SignalPayload

logger = logging.getLogger(__name__)


class Strategist:
    """LLM-powered trade decision maker."""

    def __init__(self, client: object) -> None:
        self._client = client

    async def evaluate(self, signal: SignalPayload) -> StrategistDecision | PassDecision:
        """Evaluate a signal payload and return a decision."""
        # Hard pass: no-signal alignment score
        if signal.alignment_score <= NO_SIGNAL_THRESHOLD:
            return PassDecision(
                decision=DecisionType.PASS,
                reasoning=f"Alignment score {signal.alignment_score} below threshold {NO_SIGNAL_THRESHOLD}.",
            )

        # Hard pass: trending-down regime (long-only strategy)
        if signal.regime == REGIME_TRENDING_DOWN:
            return PassDecision(
                decision=DecisionType.PASS,
                reasoning="Regime is TRENDING_DOWN. Long-only strategy: cash is the trade.",
            )

        # Call LLM
        user_prompt = build_user_prompt(signal)
        response = await self._client.complete(
            system=SYSTEM_PROMPT,
            prompt=user_prompt,
        )
        return self._parse_response(response, signal)

    def _parse_response(
        self, raw: str, signal: SignalPayload
    ) -> StrategistDecision | PassDecision:
        """Parse the LLM JSON response into a typed decision."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Strategist LLM returned invalid JSON, defaulting to PASS")
            return PassDecision(
                decision=DecisionType.PASS,
                reasoning="LLM response was not valid JSON.",
            )

        if data.get("decision") == DecisionType.PASS.value:
            return PassDecision(
                decision=DecisionType.PASS,
                reasoning=data.get("reasoning", "No reasoning provided."),
            )

        # Validate weak-signal override
        if signal.alignment_score < WEAK_THRESHOLD and not data.get("override_justification"):
            return PassDecision(
                decision=DecisionType.PASS,
                reasoning="Weak signal without override_justification.",
            )

        # Apply regime position size multiplier
        raw_size = float(data.get("position_size_pct", 0.5))
        multiplier = POSITION_SIZE_MULTIPLIER.get(signal.regime, 1.0)
        adjusted_size = raw_size * multiplier

        return StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning=data.get("reasoning", ""),
            pair=data.get("pair", signal.pair),
            side=data.get("side", "buy"),
            confidence=float(data.get("confidence", 0.0)),
            position_size_pct=adjusted_size,
            override_justification=data.get("override_justification"),
        )


class StrategistProposal:
    """Internal proposal object produced by the Strategist."""

    def __init__(
        self,
        proposal_id: str,
        agent_id: str,
        pair: str,
        side: str,
        confidence: float,
        position_size_pct: float,
        reasoning: str,
        regime: str,
        alignment_score: float,
        override_justification: str | None = None,
    ) -> None:
        self.proposal_id = proposal_id
        self.agent_id = agent_id
        self.pair = pair
        self.side = side
        self.confidence = confidence
        self.position_size_pct = position_size_pct
        self.reasoning = reasoning
        self.regime = regime
        self.alignment_score = alignment_score
        self.override_justification = override_justification

    def model_dump(self, *, mode: str = "python") -> dict:  # noqa: ARG002
        """Return a dict representation for downstream consumers."""
        return {
            "proposal_id": self.proposal_id,
            "agent_id": self.agent_id,
            "pair": self.pair,
            "side": self.side,
            "confidence": self.confidence,
            "position_size_pct": self.position_size_pct,
            "reasoning": self.reasoning,
            "regime": self.regime,
            "alignment_score": self.alignment_score,
            "override_justification": self.override_justification,
        }


def decision_to_proposal(
    decision: StrategistDecision, signal: SignalPayload, agent_id: str
) -> StrategistProposal:
    """Convert a PROPOSE decision into a StrategistProposal."""
    return StrategistProposal(
        proposal_id=str(uuid.uuid4()),
        agent_id=agent_id,
        pair=decision.pair,
        side=decision.side,
        confidence=decision.confidence,
        position_size_pct=decision.position_size_pct,
        reasoning=decision.reasoning,
        regime=signal.regime,
        alignment_score=signal.alignment_score,
        override_justification=decision.override_justification,
    )
