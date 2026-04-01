# Strategist + Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Strategist (LLM trade decisions) and Orchestrator (LangGraph pipeline wiring signal->strategy->risk->execute->audit).

**Architecture:** Strategist wraps Anthropic adapter with regime-specific prompts. Orchestrator is a LangGraph StateGraph with thin node functions that delegate to existing modules.

**Tech Stack:** langgraph, anthropic SDK (via adapter), asyncio

---

## Task 1: Strategist constants and types

**Files:**
- `backend/src/trustdesk/strategist/constants.py` (new)
- `backend/src/trustdesk/strategist/types.py` (new)

### 1a. Create `backend/src/trustdesk/strategist/constants.py`

```python
"""Strategist constants: thresholds, cycle intervals, position sizing."""

from trustdesk.core.constants import MarketRegime

# Signal alignment score thresholds
STRONG_THRESHOLD = 1.00
MODERATE_THRESHOLD = 0.80
WEAK_THRESHOLD = 0.60
NO_SIGNAL_THRESHOLD = 0.40

# Cycle intervals per regime (seconds)
CYCLE_INTERVALS: dict[MarketRegime, int] = {
    MarketRegime.TRENDING_UP: 300,    # 5 minutes
    MarketRegime.TRENDING_DOWN: 900,  # 15 minutes
    MarketRegime.RANGING: 300,        # 5 minutes
    MarketRegime.VOLATILE: 120,       # 2 minutes
}

# Position size multiplier per regime (1.0 = full size)
POSITION_SIZE_MULTIPLIER: dict[MarketRegime, float] = {
    MarketRegime.TRENDING_UP: 1.0,
    MarketRegime.TRENDING_DOWN: 0.0,   # default PASS
    MarketRegime.RANGING: 1.0,
    MarketRegime.VOLATILE: 0.5,
}

# Default cycle interval fallback
DEFAULT_CYCLE_INTERVAL = 300
```

### 1b. Create `backend/src/trustdesk/strategist/types.py`

```python
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
```

### 1c. Update `backend/src/trustdesk/strategist/__init__.py`

```python
"""Strategist: LLM-powered trade decision maker."""

from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision

__all__ = ["DecisionType", "PassDecision", "StrategistDecision"]
```

**Verification:** `python -c "from trustdesk.strategist import DecisionType, StrategistDecision, PassDecision; print('OK')"`

---

## Task 2: Strategist prompts

**Files:**
- `backend/src/trustdesk/strategist/prompts.py` (new)
- `backend/src/trustdesk/strategist/tests/test_prompts.py` (new)

### 2a. Create `backend/src/trustdesk/strategist/prompts.py`

```python
"""System and user prompt construction for the Strategist."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from trustdesk.core.constants import MarketRegime

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
PROPOSE: {"decision": "PROPOSE", "reasoning": "...", "pair": "...", "side": "buy", "confidence": 0.0-1.0, "position_size_pct": 0.0-1.0, "override_justification": "..." or null}
PASS: {"decision": "PASS", "reasoning": "..."}"""


def build_regime_context(regime: MarketRegime) -> str:
    """Return regime-specific instruction addendum."""
    regime_instructions: dict[MarketRegime, str] = {
        MarketRegime.TRENDING_UP: (
            "Current regime: TRENDING_UP. "
            "Look for pullback entries on momentum dips. Favor BTC pairs."
        ),
        MarketRegime.TRENDING_DOWN: (
            "Current regime: TRENDING_DOWN. "
            "Default action is PASS. Long-only strategy: cash is the best trade."
        ),
        MarketRegime.RANGING: (
            "Current regime: RANGING. "
            "Only consider mean-reversion trades at Bollinger Band extremes."
        ),
        MarketRegime.VOLATILE: (
            "Current regime: VOLATILE. "
            "Only STRONG signals qualify. Use 50% position sizing."
        ),
    }
    return regime_instructions.get(regime, "Current regime: UNKNOWN. Exercise caution.")


def build_user_prompt(signal: SignalPayload) -> str:
    """Build the user prompt from a SignalPayload."""
    payload_dict = signal.model_dump(mode="json")
    return (
        f"Evaluate the following signal payload and decide PROPOSE or PASS.\n\n"
        f"{build_regime_context(signal.regime)}\n\n"
        f"Signal Payload:\n```json\n{json.dumps(payload_dict, indent=2)}\n```"
    )
```

### 2b. Create `backend/src/trustdesk/strategist/tests/__init__.py`

```python
```

### 2c. Create `backend/src/trustdesk/strategist/tests/test_prompts.py`

```python
"""Tests for strategist prompt construction."""

from __future__ import annotations

from unittest.mock import MagicMock

from trustdesk.core.constants import MarketRegime
from trustdesk.strategist.prompts import (
    SYSTEM_PROMPT,
    build_regime_context,
    build_user_prompt,
)


class TestSystemPrompt:
    def test_system_prompt_contains_decision_types(self) -> None:
        assert "PROPOSE" in SYSTEM_PROMPT
        assert "PASS" in SYSTEM_PROMPT

    def test_system_prompt_contains_thresholds(self) -> None:
        assert "1.00" in SYSTEM_PROMPT
        assert "0.80" in SYSTEM_PROMPT
        assert "0.60" in SYSTEM_PROMPT
        assert "0.40" in SYSTEM_PROMPT

    def test_system_prompt_mentions_all_regimes(self) -> None:
        assert "TRENDING_UP" in SYSTEM_PROMPT
        assert "TRENDING_DOWN" in SYSTEM_PROMPT
        assert "RANGING" in SYSTEM_PROMPT
        assert "VOLATILE" in SYSTEM_PROMPT


class TestBuildRegimeContext:
    def test_trending_up(self) -> None:
        ctx = build_regime_context(MarketRegime.TRENDING_UP)
        assert "pullback" in ctx.lower()
        assert "BTC" in ctx

    def test_trending_down(self) -> None:
        ctx = build_regime_context(MarketRegime.TRENDING_DOWN)
        assert "PASS" in ctx
        assert "cash" in ctx.lower()

    def test_ranging(self) -> None:
        ctx = build_regime_context(MarketRegime.RANGING)
        assert "Bollinger" in ctx

    def test_volatile(self) -> None:
        ctx = build_regime_context(MarketRegime.VOLATILE)
        assert "50%" in ctx
        assert "STRONG" in ctx


class TestBuildUserPrompt:
    def test_user_prompt_contains_signal_data(self) -> None:
        signal = MagicMock()
        signal.regime = MarketRegime.TRENDING_UP
        signal.model_dump.return_value = {
            "pair": "BTC/USD",
            "alignment_score": 0.85,
            "regime": "TRENDING_UP",
        }
        prompt = build_user_prompt(signal)
        assert "BTC/USD" in prompt
        assert "TRENDING_UP" in prompt
        assert "PROPOSE or PASS" in prompt

    def test_user_prompt_includes_regime_context(self) -> None:
        signal = MagicMock()
        signal.regime = MarketRegime.VOLATILE
        signal.model_dump.return_value = {"pair": "ETH/USD"}
        prompt = build_user_prompt(signal)
        assert "VOLATILE" in prompt
        assert "50%" in prompt
```

**Verification:** `cd backend && python -m pytest src/trustdesk/strategist/tests/test_prompts.py -v`

---

## Task 3: Strategist cycle manager

**Files:**
- `backend/src/trustdesk/strategist/cycle.py` (new)
- `backend/src/trustdesk/strategist/tests/test_cycle.py` (new)

### 3a. Create `backend/src/trustdesk/strategist/cycle.py`

```python
"""Cycle frequency management for the Strategist."""

from __future__ import annotations

import time

from trustdesk.core.constants import MarketRegime
from trustdesk.strategist.constants import CYCLE_INTERVALS, DEFAULT_CYCLE_INTERVAL


def get_cycle_interval(regime: MarketRegime) -> int:
    """Return the cycle interval in seconds for the given regime."""
    return CYCLE_INTERVALS.get(regime, DEFAULT_CYCLE_INTERVAL)


class CycleTimer:
    """Tracks whether enough time has elapsed for the next strategist cycle."""

    def __init__(self, *, clock: callable = time.monotonic) -> None:
        self._clock = clock
        self._last_run: float | None = None

    def should_run(self, regime: MarketRegime) -> bool:
        """Return True if the cycle interval has elapsed since last run."""
        if self._last_run is None:
            return True
        interval = get_cycle_interval(regime)
        return (self._clock() - self._last_run) >= interval

    def mark_run(self) -> None:
        """Record that a cycle just ran."""
        self._last_run = self._clock()

    def reset(self) -> None:
        """Reset the timer so next should_run returns True."""
        self._last_run = None
```

### 3b. Create `backend/src/trustdesk/strategist/tests/test_cycle.py`

```python
"""Tests for strategist cycle timing."""

from __future__ import annotations

from trustdesk.core.constants import MarketRegime
from trustdesk.strategist.cycle import CycleTimer, get_cycle_interval


class TestGetCycleInterval:
    def test_trending_up_is_300(self) -> None:
        assert get_cycle_interval(MarketRegime.TRENDING_UP) == 300

    def test_trending_down_is_900(self) -> None:
        assert get_cycle_interval(MarketRegime.TRENDING_DOWN) == 900

    def test_ranging_is_300(self) -> None:
        assert get_cycle_interval(MarketRegime.RANGING) == 300

    def test_volatile_is_120(self) -> None:
        assert get_cycle_interval(MarketRegime.VOLATILE) == 120


class TestCycleTimer:
    def test_first_call_should_run(self) -> None:
        timer = CycleTimer()
        assert timer.should_run(MarketRegime.TRENDING_UP) is True

    def test_immediately_after_mark_should_not_run(self) -> None:
        current_time = 1000.0
        timer = CycleTimer(clock=lambda: current_time)
        timer.mark_run()
        assert timer.should_run(MarketRegime.TRENDING_UP) is False

    def test_after_interval_should_run(self) -> None:
        times = iter([1000.0, 1000.0, 1301.0])
        timer = CycleTimer(clock=lambda: next(times))
        timer.mark_run()
        assert timer.should_run(MarketRegime.TRENDING_UP) is True

    def test_volatile_shorter_interval(self) -> None:
        times = iter([1000.0, 1000.0, 1121.0])
        timer = CycleTimer(clock=lambda: next(times))
        timer.mark_run()
        assert timer.should_run(MarketRegime.VOLATILE) is True

    def test_reset_makes_should_run_true(self) -> None:
        current_time = 1000.0
        timer = CycleTimer(clock=lambda: current_time)
        timer.mark_run()
        assert timer.should_run(MarketRegime.TRENDING_UP) is False
        timer.reset()
        assert timer.should_run(MarketRegime.TRENDING_UP) is True
```

**Verification:** `cd backend && python -m pytest src/trustdesk/strategist/tests/test_cycle.py -v`

---

## Task 4: Strategist main module

**Files:**
- `backend/src/trustdesk/strategist/strategist.py` (new)
- `backend/src/trustdesk/strategist/tests/test_strategist.py` (new)

### 4a. Create `backend/src/trustdesk/strategist/strategist.py`

```python
"""Strategist: receives SignalPayload, calls LLM, returns TradeProposal or None."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from trustdesk.core.constants import MarketRegime
from trustdesk.strategist.constants import (
    NO_SIGNAL_THRESHOLD,
    POSITION_SIZE_MULTIPLIER,
    WEAK_THRESHOLD,
)
from trustdesk.strategist.prompts import SYSTEM_PROMPT, build_user_prompt
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision

if TYPE_CHECKING:
    from trustdesk.adapters.anthropic.client import AnthropicClient
    from trustdesk.schemas import SignalPayload, TradeProposal

logger = logging.getLogger(__name__)


class Strategist:
    """LLM-powered trade decision maker."""

    def __init__(self, client: AnthropicClient) -> None:
        self._client = client

    async def evaluate(self, signal: SignalPayload) -> StrategistDecision | PassDecision:
        """Evaluate a signal payload and return a decision."""
        # Hard pass: no-signal or trending-down regime
        if signal.alignment_score <= NO_SIGNAL_THRESHOLD:
            return PassDecision(
                decision=DecisionType.PASS,
                reasoning=f"Alignment score {signal.alignment_score} below threshold {NO_SIGNAL_THRESHOLD}.",
            )

        if signal.regime == MarketRegime.TRENDING_DOWN:
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


def decision_to_proposal(
    decision: StrategistDecision, signal: SignalPayload, agent_id: str
) -> TradeProposal:
    """Convert a PROPOSE decision into a TradeProposal schema."""
    from trustdesk.schemas import TradeProposal

    return TradeProposal(
        proposal_id=str(uuid.uuid4()),
        agent_id=agent_id,
        pair=decision.pair,
        side=decision.side,
        confidence=decision.confidence,
        position_size_pct=decision.position_size_pct,
        reasoning=decision.reasoning,
        signal_payload=signal,
        regime=signal.regime,
    )
```

### 4b. Create `backend/src/trustdesk/strategist/tests/test_strategist.py`

```python
"""Tests for the Strategist module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.core.constants import MarketRegime
from trustdesk.strategist.strategist import Strategist, decision_to_proposal
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


def _make_signal(
    alignment_score: float = 0.85,
    regime: MarketRegime = MarketRegime.TRENDING_UP,
    pair: str = "BTC/USD",
) -> MagicMock:
    signal = MagicMock()
    signal.alignment_score = alignment_score
    signal.regime = regime
    signal.pair = pair
    signal.model_dump.return_value = {
        "pair": pair,
        "alignment_score": alignment_score,
        "regime": regime.value,
    }
    return signal


class TestStrategistEvaluate:
    @pytest.mark.asyncio
    async def test_no_signal_returns_pass(self) -> None:
        client = AsyncMock()
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.30)

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert result.decision == DecisionType.PASS
        assert "0.3" in result.reasoning
        client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_trending_down_returns_pass(self) -> None:
        client = AsyncMock()
        strategist = Strategist(client)
        signal = _make_signal(regime=MarketRegime.TRENDING_DOWN)

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert "TRENDING_DOWN" in result.reasoning
        client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_propose_response(self) -> None:
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Strong pullback entry on BTC.",
            "pair": "BTC/USD",
            "side": "buy",
            "confidence": 0.9,
            "position_size_pct": 0.8,
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.85)

        result = await strategist.evaluate(signal)

        assert isinstance(result, StrategistDecision)
        assert result.decision == DecisionType.PROPOSE
        assert result.pair == "BTC/USD"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_llm_pass_response(self) -> None:
        llm_response = json.dumps({
            "decision": "PASS",
            "reasoning": "No clear signal.",
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal()

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert result.reasoning == "No clear signal."

    @pytest.mark.asyncio
    async def test_invalid_json_returns_pass(self) -> None:
        client = AsyncMock()
        client.complete.return_value = "this is not json"
        strategist = Strategist(client)
        signal = _make_signal()

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert "not valid JSON" in result.reasoning

    @pytest.mark.asyncio
    async def test_weak_signal_without_override_returns_pass(self) -> None:
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Taking a chance.",
            "pair": "ETH/USD",
            "side": "buy",
            "confidence": 0.7,
            "position_size_pct": 0.5,
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(alignment_score=0.55)

        result = await strategist.evaluate(signal)

        assert isinstance(result, PassDecision)
        assert "override_justification" in result.reasoning

    @pytest.mark.asyncio
    async def test_volatile_regime_halves_position_size(self) -> None:
        llm_response = json.dumps({
            "decision": "PROPOSE",
            "reasoning": "Strong signal in vol regime.",
            "pair": "BTC/USD",
            "side": "buy",
            "confidence": 1.0,
            "position_size_pct": 1.0,
        })
        client = AsyncMock()
        client.complete.return_value = llm_response
        strategist = Strategist(client)
        signal = _make_signal(
            alignment_score=1.0,
            regime=MarketRegime.VOLATILE,
        )

        result = await strategist.evaluate(signal)

        assert isinstance(result, StrategistDecision)
        assert result.position_size_pct == pytest.approx(0.5)


class TestDecisionToProposal:
    def test_converts_decision_to_proposal(self) -> None:
        decision = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )
        signal = _make_signal()

        proposal = decision_to_proposal(decision, signal, agent_id="agent-1")

        assert proposal.pair == "BTC/USD"
        assert proposal.agent_id == "agent-1"
        assert proposal.confidence == 0.9
```

**Verification:** `cd backend && python -m pytest src/trustdesk/strategist/tests/test_strategist.py -v`

---

## Task 5: Orchestrator state and types

**Files:**
- `backend/src/trustdesk/orchestrator/constants.py` (new)
- `backend/src/trustdesk/orchestrator/types.py` (new)
- `backend/src/trustdesk/orchestrator/state.py` (new)
- `backend/src/trustdesk/orchestrator/tests/test_state.py` (new)

### 5a. Create `backend/src/trustdesk/orchestrator/constants.py`

```python
"""Orchestrator constants."""

# Queue names
PROPOSALS_QUEUE = "proposals"
VERDICTS_QUEUE = "verdicts"

# Position lifecycle
MAX_POSITION_DURATION_SECONDS = 86400  # 24 hours
POSITION_CHECK_INTERVAL_SECONDS = 30

# Node names (for graph definition)
NODE_SIGNAL = "signal_engine"
NODE_STRATEGIST = "strategist"
NODE_REPUTATION = "reputation_check"
NODE_RISK = "risk_validate"
NODE_EXECUTE = "execute"
NODE_AUDIT = "audit"
NODE_AUDIT_PASS = "audit_pass"
```

### 5b. Create `backend/src/trustdesk/orchestrator/types.py`

```python
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
```

### 5c. Create `backend/src/trustdesk/orchestrator/state.py`

```python
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
```

### 5d. Create `backend/src/trustdesk/orchestrator/tests/__init__.py`

```python
```

### 5e. Create `backend/src/trustdesk/orchestrator/tests/test_state.py`

```python
"""Tests for orchestrator state schema."""

from __future__ import annotations

from trustdesk.orchestrator.state import PipelineState


class TestPipelineState:
    def test_empty_state_is_valid(self) -> None:
        state: PipelineState = {}
        assert state == {}

    def test_partial_state_is_valid(self) -> None:
        state: PipelineState = {
            "correlation_id": "corr-123",
            "agent_id": "agent-1",
        }
        assert state["correlation_id"] == "corr-123"

    def test_full_state_is_valid(self) -> None:
        state: PipelineState = {
            "correlation_id": "corr-123",
            "agent_id": "agent-1",
            "signal_payload": {"pair": "BTC/USD"},
            "regime": "TRENDING_UP",
            "decision_type": "PROPOSE",
            "proposal": {"pair": "BTC/USD", "side": "buy"},
            "pass_reasoning": None,
            "agent_tier": "PROVEN",
            "verdict": {"approved": True},
            "verdict_approved": True,
            "execution_result": {"order_id": "ord-1"},
            "order_id": "ord-1",
            "audited": True,
            "error": None,
        }
        assert state["verdict_approved"] is True
        assert state["order_id"] == "ord-1"
```

**Verification:** `cd backend && python -m pytest src/trustdesk/orchestrator/tests/test_state.py -v`

---

## Task 6: Orchestrator node functions

**Files:**
- `backend/src/trustdesk/orchestrator/nodes.py` (new)
- `backend/src/trustdesk/orchestrator/tests/test_nodes.py` (new)

### 6a. Create `backend/src/trustdesk/orchestrator/nodes.py`

```python
"""Graph node functions for the orchestrator pipeline.

Each node is a thin wrapper: takes PipelineState, calls the appropriate
module, and returns state updates. Business logic stays in the modules.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from trustdesk.orchestrator.state import PipelineState
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
    from trustdesk.strategist.strategist import decision_to_proposal

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
    queue: Any,
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
```

### 6b. Create `backend/src/trustdesk/orchestrator/tests/test_nodes.py`

```python
"""Tests for orchestrator node functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.orchestrator.nodes import (
    audit_node,
    audit_pass_node,
    execute_node,
    reputation_node,
    risk_node,
    signal_engine_node,
    strategist_node,
)
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


class TestSignalEngineNode:
    @pytest.mark.asyncio
    async def test_populates_signal_payload(self) -> None:
        engine = AsyncMock()
        signal = MagicMock()
        signal.model_dump.return_value = {"pair": "BTC/USD", "alignment_score": 0.9}
        signal.regime.value = "TRENDING_UP"
        engine.generate.return_value = signal

        result = await signal_engine_node({}, engine=engine)

        assert result["signal_payload"]["pair"] == "BTC/USD"
        assert result["regime"] == "TRENDING_UP"


class TestStrategistNode:
    @pytest.mark.asyncio
    async def test_pass_decision(self) -> None:
        strategist = AsyncMock()
        strategist.evaluate.return_value = PassDecision(
            decision=DecisionType.PASS,
            reasoning="No signal.",
        )
        signal_cls = MagicMock()
        signal_cls.model_validate.return_value = MagicMock()

        state = {"signal_payload": {"pair": "BTC/USD"}, "agent_id": "agent-1"}
        result = await strategist_node(state, strategist=strategist, signal_cls=signal_cls)

        assert result["decision_type"] == "PASS"
        assert result["proposal"] is None
        assert result["pass_reasoning"] == "No signal."

    @pytest.mark.asyncio
    async def test_propose_decision(self) -> None:
        decision = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )
        strategist = AsyncMock()
        strategist.evaluate.return_value = decision
        signal_cls = MagicMock()
        mock_signal = MagicMock()
        mock_signal.regime = "TRENDING_UP"
        signal_cls.model_validate.return_value = mock_signal

        mock_proposal = MagicMock()
        mock_proposal.model_dump.return_value = {"pair": "BTC/USD", "side": "buy"}

        state = {"signal_payload": {"pair": "BTC/USD"}, "agent_id": "agent-1"}

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mock_proposal,
        ):
            result = await strategist_node(state, strategist=strategist, signal_cls=signal_cls)

        assert result["decision_type"] == "PROPOSE"
        assert result["proposal"] is not None


class TestReputationNode:
    @pytest.mark.asyncio
    async def test_returns_tier(self) -> None:
        rep_engine = AsyncMock()
        tier_mock = MagicMock()
        tier_mock.value = "PROVEN"
        rep_engine.get_tier.return_value = tier_mock

        state = {"agent_id": "agent-1"}
        result = await reputation_node(state, reputation_engine=rep_engine)

        assert result["agent_tier"] == "PROVEN"


class TestRiskNode:
    @pytest.mark.asyncio
    async def test_no_proposal_returns_not_approved(self) -> None:
        risk_mgr = AsyncMock()
        queue = AsyncMock()

        state = {"proposal": None}
        result = await risk_node(state, risk_manager=risk_mgr, queue=queue)

        assert result["verdict_approved"] is False

    @pytest.mark.asyncio
    async def test_approved_verdict(self) -> None:
        verdict = MagicMock()
        verdict.approved = True
        verdict.model_dump.return_value = {"approved": True}
        risk_mgr = AsyncMock()
        risk_mgr.evaluate.return_value = verdict
        queue = AsyncMock()

        state = {"proposal": {"pair": "BTC/USD"}, "agent_tier": "PROVEN"}
        result = await risk_node(state, risk_manager=risk_mgr, queue=queue)

        assert result["verdict_approved"] is True


class TestExecuteNode:
    @pytest.mark.asyncio
    async def test_not_approved_skips_execution(self) -> None:
        kraken = AsyncMock()
        state = {"verdict_approved": False}
        result = await execute_node(state, kraken=kraken)

        assert result["execution_result"] is None
        kraken.place_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_approved_places_order(self) -> None:
        kraken = AsyncMock()
        kraken.place_order.return_value = {"order_id": "ord-123", "status": "filled"}

        state = {
            "verdict_approved": True,
            "proposal": {"pair": "BTC/USD", "side": "buy", "position_size_pct": 0.5},
        }
        result = await execute_node(state, kraken=kraken)

        assert result["order_id"] == "ord-123"
        kraken.place_order.assert_called_once()


class TestAuditNodes:
    @pytest.mark.asyncio
    async def test_audit_node_records(self) -> None:
        auditor = AsyncMock()
        state = {"correlation_id": "corr-1"}
        result = await audit_node(state, auditor=auditor)

        assert result["audited"] is True
        auditor.record.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_node_swallows_errors(self) -> None:
        auditor = AsyncMock()
        auditor.record.side_effect = RuntimeError("boom")
        result = await audit_node({}, auditor=auditor)

        assert result["audited"] is True

    @pytest.mark.asyncio
    async def test_audit_pass_node_records(self) -> None:
        auditor = AsyncMock()
        state = {"correlation_id": "corr-1", "pass_reasoning": "No signal."}
        result = await audit_pass_node(state, auditor=auditor)

        assert result["audited"] is True
        auditor.record_pass.assert_called_once()
```

**Verification:** `cd backend && python -m pytest src/trustdesk/orchestrator/tests/test_nodes.py -v`

---

## Task 7: Orchestrator LangGraph graph

**Files:**
- `backend/src/trustdesk/orchestrator/graph.py` (new)
- `backend/src/trustdesk/orchestrator/tests/test_graph.py` (new)

### 7a. Create `backend/src/trustdesk/orchestrator/graph.py`

```python
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
) -> StateGraph:
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
```

### 7b. Create `backend/src/trustdesk/orchestrator/tests/test_graph.py`

```python
"""Tests for the orchestrator LangGraph graph.

All modules are mocked. These tests verify the graph flow, not individual modules.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.orchestrator.graph import build_graph
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision


def _build_mocks(
    *,
    decision: str = "PROPOSE",
    approved: bool = True,
) -> dict:
    """Build a full set of mocks for the graph."""
    signal = MagicMock()
    signal.model_dump.return_value = {"pair": "BTC/USD", "alignment_score": 0.9}
    signal.regime.value = "TRENDING_UP"

    engine = AsyncMock()
    engine.generate.return_value = signal

    if decision == "PASS":
        eval_result = PassDecision(
            decision=DecisionType.PASS, reasoning="No signal."
        )
    else:
        eval_result = StrategistDecision(
            decision=DecisionType.PROPOSE,
            reasoning="Good entry.",
            pair="BTC/USD",
            side="buy",
            confidence=0.9,
            position_size_pct=0.8,
        )

    strategist = AsyncMock()
    strategist.evaluate.return_value = eval_result

    signal_cls = MagicMock()
    signal_cls.model_validate.return_value = signal

    tier_mock = MagicMock()
    tier_mock.value = "PROVEN"
    reputation_engine = AsyncMock()
    reputation_engine.get_tier.return_value = tier_mock

    verdict = MagicMock()
    verdict.approved = approved
    verdict.model_dump.return_value = {"approved": approved}
    risk_manager = AsyncMock()
    risk_manager.evaluate.return_value = verdict

    queue = AsyncMock()

    kraken = AsyncMock()
    kraken.place_order.return_value = {"order_id": "ord-1", "status": "filled"}

    auditor = AsyncMock()

    # For decision_to_proposal mock
    proposal_mock = MagicMock()
    proposal_mock.model_dump.return_value = {
        "pair": "BTC/USD",
        "side": "buy",
        "position_size_pct": 0.8,
    }

    return {
        "engine": engine,
        "strategist": strategist,
        "signal_cls": signal_cls,
        "reputation_engine": reputation_engine,
        "risk_manager": risk_manager,
        "queue": queue,
        "kraken": kraken,
        "auditor": auditor,
        "proposal_mock": proposal_mock,
    }


class TestGraphProposePath:
    @pytest.mark.asyncio
    async def test_full_propose_approve_execute_flow(self) -> None:
        mocks = _build_mocks(decision="PROPOSE", approved=True)
        from unittest.mock import patch

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mocks["proposal_mock"],
        ):
            graph = build_graph(
                engine=mocks["engine"],
                strategist=mocks["strategist"],
                signal_cls=mocks["signal_cls"],
                reputation_engine=mocks["reputation_engine"],
                risk_manager=mocks["risk_manager"],
                queue=mocks["queue"],
                kraken=mocks["kraken"],
                auditor=mocks["auditor"],
            )
            result = await graph.ainvoke({
                "correlation_id": "test-corr",
                "agent_id": "agent-1",
            })

        assert result["decision_type"] == "PROPOSE"
        assert result["verdict_approved"] is True
        assert result["order_id"] == "ord-1"
        assert result["audited"] is True
        mocks["kraken"].place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_rejected_no_execution(self) -> None:
        mocks = _build_mocks(decision="PROPOSE", approved=False)
        from unittest.mock import patch

        with patch(
            "trustdesk.orchestrator.nodes.decision_to_proposal",
            return_value=mocks["proposal_mock"],
        ):
            graph = build_graph(
                engine=mocks["engine"],
                strategist=mocks["strategist"],
                signal_cls=mocks["signal_cls"],
                reputation_engine=mocks["reputation_engine"],
                risk_manager=mocks["risk_manager"],
                queue=mocks["queue"],
                kraken=mocks["kraken"],
                auditor=mocks["auditor"],
            )
            result = await graph.ainvoke({
                "correlation_id": "test-corr",
                "agent_id": "agent-1",
            })

        assert result["verdict_approved"] is False
        assert result["execution_result"] is None
        assert result["audited"] is True


class TestGraphPassPath:
    @pytest.mark.asyncio
    async def test_pass_skips_risk_and_execution(self) -> None:
        mocks = _build_mocks(decision="PASS")

        graph = build_graph(
            engine=mocks["engine"],
            strategist=mocks["strategist"],
            signal_cls=mocks["signal_cls"],
            reputation_engine=mocks["reputation_engine"],
            risk_manager=mocks["risk_manager"],
            queue=mocks["queue"],
            kraken=mocks["kraken"],
            auditor=mocks["auditor"],
        )
        result = await graph.ainvoke({
            "correlation_id": "test-corr",
            "agent_id": "agent-1",
        })

        assert result["decision_type"] == "PASS"
        assert result["audited"] is True
        mocks["reputation_engine"].get_tier.assert_not_called()
        mocks["risk_manager"].evaluate.assert_not_called()
        mocks["kraken"].place_order.assert_not_called()
        mocks["auditor"].record_pass.assert_called_once()
```

**Verification:** `cd backend && python -m pytest src/trustdesk/orchestrator/tests/test_graph.py -v`

---

## Task 8: Orchestrator position lifecycle

**Files:**
- `backend/src/trustdesk/orchestrator/lifecycle.py` (new)
- `backend/src/trustdesk/orchestrator/tests/test_lifecycle.py` (new)

### 8a. Create `backend/src/trustdesk/orchestrator/lifecycle.py`

```python
"""Position lifecycle management: monitoring, exits, and callbacks."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from trustdesk.orchestrator.constants import MAX_POSITION_DURATION_SECONDS

logger = logging.getLogger(__name__)


class ExitReason(str, Enum):
    """Why a position was closed."""

    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    INVALIDATION = "invalidation"
    MANUAL = "manual"


@dataclass
class PositionState:
    """Tracks an open position's lifecycle."""

    order_id: str
    pair: str
    side: str
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float | None = None
    opened_at: float = field(default_factory=time.time)
    closed: bool = False
    exit_reason: ExitReason | None = None


class PositionMonitor:
    """Monitors open positions for exit conditions."""

    def __init__(self, *, clock: callable = time.time) -> None:
        self._clock = clock
        self._positions: dict[str, PositionState] = {}

    def track(self, position: PositionState) -> None:
        """Start tracking a position."""
        self._positions[position.order_id] = position

    def get(self, order_id: str) -> PositionState | None:
        """Get a tracked position by order_id."""
        return self._positions.get(order_id)

    def check_exit(
        self, order_id: str, current_price: float
    ) -> ExitReason | None:
        """Check if a position should be exited. Returns reason or None."""
        pos = self._positions.get(order_id)
        if pos is None or pos.closed:
            return None

        # Time-based exit
        elapsed = self._clock() - pos.opened_at
        if elapsed >= MAX_POSITION_DURATION_SECONDS:
            return ExitReason.TIME_EXIT

        # Stop loss
        if pos.side == "buy" and current_price <= pos.stop_loss:
            return ExitReason.STOP_LOSS
        if pos.side == "sell" and current_price >= pos.stop_loss:
            return ExitReason.STOP_LOSS

        # Take profit 2 (checked first for full exit)
        if pos.tp2 is not None:
            if pos.side == "buy" and current_price >= pos.tp2:
                return ExitReason.TP2_HIT
            if pos.side == "sell" and current_price <= pos.tp2:
                return ExitReason.TP2_HIT

        # Take profit 1
        if pos.side == "buy" and current_price >= pos.tp1:
            return ExitReason.TP1_HIT
        if pos.side == "sell" and current_price <= pos.tp1:
            return ExitReason.TP1_HIT

        return None

    def close(self, order_id: str, reason: ExitReason) -> PositionState | None:
        """Mark a position as closed."""
        pos = self._positions.get(order_id)
        if pos is None:
            return None
        pos.closed = True
        pos.exit_reason = reason
        return pos

    @property
    def open_positions(self) -> list[PositionState]:
        """Return all open (not closed) positions."""
        return [p for p in self._positions.values() if not p.closed]
```

### 8b. Create `backend/src/trustdesk/orchestrator/tests/test_lifecycle.py`

```python
"""Tests for position lifecycle management."""

from __future__ import annotations

from trustdesk.orchestrator.lifecycle import (
    ExitReason,
    PositionMonitor,
    PositionState,
)


def _make_position(**overrides) -> PositionState:
    defaults = {
        "order_id": "ord-1",
        "pair": "BTC/USD",
        "side": "buy",
        "entry_price": 50000.0,
        "stop_loss": 48000.0,
        "tp1": 52000.0,
        "tp2": 55000.0,
        "opened_at": 1000.0,
    }
    defaults.update(overrides)
    return PositionState(**defaults)


class TestPositionMonitor:
    def test_track_and_get(self) -> None:
        monitor = PositionMonitor()
        pos = _make_position()
        monitor.track(pos)
        assert monitor.get("ord-1") is pos

    def test_get_unknown_returns_none(self) -> None:
        monitor = PositionMonitor()
        assert monitor.get("unknown") is None

    def test_open_positions(self) -> None:
        monitor = PositionMonitor()
        monitor.track(_make_position(order_id="a"))
        monitor.track(_make_position(order_id="b"))
        assert len(monitor.open_positions) == 2
        monitor.close("a", ExitReason.MANUAL)
        assert len(monitor.open_positions) == 1


class TestCheckExit:
    def test_no_exit_in_range(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position())
        assert monitor.check_exit("ord-1", current_price=50500.0) is None

    def test_stop_loss_buy(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="buy", stop_loss=48000.0))
        assert monitor.check_exit("ord-1", current_price=47500.0) == ExitReason.STOP_LOSS

    def test_stop_loss_sell(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="sell", stop_loss=52000.0))
        assert monitor.check_exit("ord-1", current_price=52500.0) == ExitReason.STOP_LOSS

    def test_tp1_hit_buy(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="buy", tp1=52000.0, tp2=None))
        assert monitor.check_exit("ord-1", current_price=52500.0) == ExitReason.TP1_HIT

    def test_tp2_hit_buy(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="buy", tp1=52000.0, tp2=55000.0))
        assert monitor.check_exit("ord-1", current_price=56000.0) == ExitReason.TP2_HIT

    def test_time_exit(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1000.0 + 86401.0)
        monitor.track(_make_position(opened_at=1000.0))
        assert monitor.check_exit("ord-1", current_price=50500.0) == ExitReason.TIME_EXIT

    def test_closed_position_returns_none(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position())
        monitor.close("ord-1", ExitReason.MANUAL)
        assert monitor.check_exit("ord-1", current_price=47000.0) is None

    def test_tp1_hit_sell(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="sell", tp1=48000.0, tp2=None))
        assert monitor.check_exit("ord-1", current_price=47500.0) == ExitReason.TP1_HIT

    def test_tp2_hit_sell(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="sell", tp1=48000.0, tp2=45000.0))
        assert monitor.check_exit("ord-1", current_price=44000.0) == ExitReason.TP2_HIT


class TestClose:
    def test_close_marks_position(self) -> None:
        monitor = PositionMonitor()
        monitor.track(_make_position())
        closed = monitor.close("ord-1", ExitReason.STOP_LOSS)
        assert closed is not None
        assert closed.closed is True
        assert closed.exit_reason == ExitReason.STOP_LOSS

    def test_close_unknown_returns_none(self) -> None:
        monitor = PositionMonitor()
        assert monitor.close("unknown", ExitReason.MANUAL) is None
```

**Verification:** `cd backend && python -m pytest src/trustdesk/orchestrator/tests/test_lifecycle.py -v`

---

## Task 9: Orchestrator `__init__.py` and final wiring

**Files:**
- `backend/src/trustdesk/orchestrator/__init__.py` (update)

### 9a. Update `backend/src/trustdesk/orchestrator/__init__.py`

```python
"""Orchestrator: LangGraph pipeline wiring signal -> strategy -> risk -> execute -> audit."""

from trustdesk.orchestrator.graph import build_graph
from trustdesk.orchestrator.lifecycle import ExitReason, PositionMonitor, PositionState
from trustdesk.orchestrator.state import PipelineState

__all__ = [
    "ExitReason",
    "PipelineState",
    "PositionMonitor",
    "PositionState",
    "build_graph",
]
```

### 9b. Update `backend/src/trustdesk/strategist/__init__.py` (final version)

```python
"""Strategist: LLM-powered trade decision maker."""

from trustdesk.strategist.cycle import CycleTimer, get_cycle_interval
from trustdesk.strategist.strategist import Strategist, decision_to_proposal
from trustdesk.strategist.types import DecisionType, PassDecision, StrategistDecision

__all__ = [
    "CycleTimer",
    "DecisionType",
    "PassDecision",
    "Strategist",
    "StrategistDecision",
    "decision_to_proposal",
    "get_cycle_interval",
]
```

**Verification:**
```bash
cd backend
python -c "from trustdesk.strategist import Strategist, CycleTimer, DecisionType; print('Strategist OK')"
python -c "from trustdesk.orchestrator import build_graph, PipelineState, PositionMonitor; print('Orchestrator OK')"
python -m pytest src/trustdesk/strategist/tests/ src/trustdesk/orchestrator/tests/ -v
```

---

## Summary

| Task | Files | Tests | What |
|------|-------|-------|------|
| 1 | constants.py, types.py, __init__.py | (import check) | Strategist foundation types |
| 2 | prompts.py | test_prompts.py | System/user prompt construction |
| 3 | cycle.py | test_cycle.py | Regime-based cycle timing |
| 4 | strategist.py | test_strategist.py | Main LLM decision logic |
| 5 | constants.py, types.py, state.py | test_state.py | Orchestrator state schema |
| 6 | nodes.py | test_nodes.py | Thin graph node functions |
| 7 | graph.py | test_graph.py | LangGraph StateGraph wiring |
| 8 | lifecycle.py | test_lifecycle.py | Position monitoring + exits |
| 9 | __init__.py (x2) | (import check) | Public API exports |

**Total new files:** 18 source + 8 test = 26 files
**Estimated new tests:** ~45 tests
**All modules mocked in orchestrator tests** -- no integration dependencies.
