"""System and user prompt construction for the Strategist."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from trustdesk.strategist.constants import (
    REGIME_RANGING,
    REGIME_TRENDING_DOWN,
    REGIME_TRENDING_UP,
    REGIME_VOLATILE,
)

if TYPE_CHECKING:
    from trustdesk.schemas import SignalPayload

SYSTEM_PROMPT = """You are TrustDesk's Strategist, a senior quantitative analyst.
You receive structured signal payloads from the Signal Engine.
You NEVER calculate indicators yourself. All math is pre-computed.

Your job:
1. Interpret signals in context of current regime.
2. Decide: PROPOSE or PASS.
3. If proposing, provide explicit reasoning.

Decision thresholds based on Signal Alignment Score:
- STRONG (1.00): Always eligible to propose.
- MODERATE (>=0.80): Default path, propose if context supports.
- WEAK (>=0.60): Only propose with override_justification explaining why.
- NO_SIGNAL (<=0.40): Always output PASS.

Regime-specific rules:
- TRENDING_UP: Look for pullback entries, favor BTC. Propose long entries.
- TRENDING_DOWN: Default PASS. Long-only strategy means cash is the trade.
- RANGING: Mean-reversion at Bollinger Band extremes only.
- VOLATILE: Only STRONG signals qualify. Use 50% position size.

You MUST respond with valid JSON matching one of these schemas:
PROPOSE: {"decision": "PROPOSE", "reasoning": "...", "pair": "...", "side": "buy",
"confidence": 0.0-1.0, "position_size_pct": 0.0-1.0, "override_justification": "..." or null}
PASS: {"decision": "PASS", "reasoning": "..."}"""


def build_regime_context(regime: str) -> str:
    """Return regime-specific instruction addendum."""
    regime_instructions: dict[str, str] = {
        REGIME_TRENDING_UP: (
            "Current regime: TRENDING_UP. "
            "Look for pullback entries on momentum dips. Favor BTC pairs."
        ),
        REGIME_TRENDING_DOWN: (
            "Current regime: TRENDING_DOWN. "
            "Default action is PASS. Long-only strategy: cash is the best trade."
        ),
        REGIME_RANGING: (
            "Current regime: RANGING. "
            "Only consider mean-reversion trades at Bollinger Band extremes."
        ),
        REGIME_VOLATILE: (
            "Current regime: VOLATILE. "
            "Only STRONG signals qualify. Use 50% position sizing."
        ),
    }
    return regime_instructions.get(regime, f"Current regime: {regime}. Exercise caution.")


def build_user_prompt(signal: SignalPayload) -> str:
    """Build the user prompt from a SignalPayload."""
    payload_dict = signal.model_dump(mode="json")
    regime = signal.regime
    return (
        f"Evaluate the following signal payload and decide PROPOSE or PASS.\n\n"
        f"{build_regime_context(regime)}\n\n"
        f"Signal Payload:\n```json\n{json.dumps(payload_dict, indent=2)}\n```"
    )
