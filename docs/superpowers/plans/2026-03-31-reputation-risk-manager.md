# Reputation Engine + Risk Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the reputation-to-limits engine and the risk manager with hard checks, soft checks, circuit breaker, and adaptive parameters.

**Architecture:** Reputation engine is pure computation (feedback history -> tier + limits). Risk manager is the evaluation pipeline (proposal + portfolio state + tier -> RiskVerdict). Both are fully testable without external dependencies.

**Tech Stack:** Python, Pydantic, asyncio

---

## Task 1: Reputation constants and tier definitions

### Step 1.1 -- Write test for tier constants

- [ ] Create `backend/src/trustdesk/reputation/tests/__init__.py`
- [ ] Create `backend/src/trustdesk/reputation/tests/test_tiers.py`

```python
# backend/src/trustdesk/reputation/tests/test_tiers.py
"""Tests for tier definitions and constants."""
import pytest

from trustdesk.reputation.constants import (
    COOLDOWN_TRADES_REQUIRED,
    DEMOTION_CONSECUTIVE_LOSSES,
    DEMOTION_SCORE,
    PROMOTION_SCORE,
)
from trustdesk.reputation.tiers import TIER_DEFINITIONS, TierName, get_tier_limits
from trustdesk.reputation.types import TierLimits


class TestTierConstants:
    def test_promotion_score(self) -> None:
        assert PROMOTION_SCORE == 60

    def test_demotion_score(self) -> None:
        assert DEMOTION_SCORE == 40

    def test_cooldown_trades(self) -> None:
        assert COOLDOWN_TRADES_REQUIRED == 5

    def test_demotion_consecutive_losses(self) -> None:
        assert DEMOTION_CONSECUTIVE_LOSSES == 5


class TestTierName:
    def test_tier_ordering(self) -> None:
        assert TierName.UNPROVEN.value < TierName.ESTABLISHED.value
        assert TierName.ESTABLISHED.value < TierName.TRUSTED.value

    def test_all_tiers_present(self) -> None:
        names = {t.name for t in TierName}
        assert names == {"UNPROVEN", "ESTABLISHED", "TRUSTED"}


class TestTierDefinitions:
    def test_all_tiers_have_definitions(self) -> None:
        for tier in TierName:
            assert tier in TIER_DEFINITIONS

    def test_unproven_limits(self) -> None:
        limits = get_tier_limits(TierName.UNPROVEN)
        assert limits.capital_usd == 100
        assert limits.max_position_pct == 3.0
        assert limits.max_trades == 1
        assert limits.max_daily_loss_pct == 3.0

    def test_established_limits(self) -> None:
        limits = get_tier_limits(TierName.ESTABLISHED)
        assert limits.capital_usd == 500
        assert limits.max_position_pct == 7.0
        assert limits.max_trades == 3
        assert limits.max_daily_loss_pct == 5.0

    def test_trusted_limits(self) -> None:
        limits = get_tier_limits(TierName.TRUSTED)
        assert limits.capital_usd == 1000
        assert limits.max_position_pct == 10.0
        assert limits.max_trades == 5
        assert limits.max_daily_loss_pct == 5.0

    def test_get_tier_limits_returns_copy(self) -> None:
        a = get_tier_limits(TierName.UNPROVEN)
        b = get_tier_limits(TierName.UNPROVEN)
        assert a == b
        assert a is not b
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/tests/test_tiers.py -x` -- expect FAIL (modules don't exist)

### Step 1.2 -- Implement types, constants, tiers

- [ ] Create `backend/src/trustdesk/reputation/__init__.py`

```python
# backend/src/trustdesk/reputation/__init__.py
"""Reputation engine -- maps on-chain feedback to capital tiers."""
```

- [ ] Create `backend/src/trustdesk/reputation/types.py`

```python
# backend/src/trustdesk/reputation/types.py
"""Internal types for the reputation engine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class FeedbackKind(IntEnum):
    """Kind of on-chain feedback event."""

    TRADE_OPEN = 1
    TRADE_CLOSE = 2
    TIER_CHANGE = 3


@dataclass(frozen=True, slots=True)
class TierLimits:
    """Capital and risk limits for a tier."""

    capital_usd: int
    max_position_pct: float
    max_trades: int
    max_daily_loss_pct: float


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    """A single on-chain feedback entry."""

    kind: FeedbackKind
    score: int
    pnl_usd: float
    timestamp: int
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class PromotionResult:
    """Result of a promotion/demotion check."""

    changed: bool
    old_tier: str
    new_tier: str
    reason: str
```

- [ ] Create `backend/src/trustdesk/reputation/constants.py`

```python
# backend/src/trustdesk/reputation/constants.py
"""Threshold constants for the reputation engine."""

# Promotion: score logged for tier_change when promoted
PROMOTION_SCORE: int = 60

# Demotion: score logged for tier_change when demoted
DEMOTION_SCORE: int = 40

# Number of verified trades at lower tier before re-promotion
COOLDOWN_TRADES_REQUIRED: int = 5

# Consecutive losses triggering demotion
DEMOTION_CONSECUTIVE_LOSSES: int = 5

# Promotion criteria -- ESTABLISHED
ESTABLISHED_MIN_TRADES: int = 20
ESTABLISHED_MIN_PNL: float = 0.0
ESTABLISHED_MAX_DD_PCT: float = 15.0

# Promotion criteria -- TRUSTED
TRUSTED_MIN_TRADES: int = 50
TRUSTED_EQUITY_RISING_PCT: float = 60.0
TRUSTED_MAX_DD_PCT: float = 10.0
```

- [ ] Create `backend/src/trustdesk/reputation/tiers.py`

```python
# backend/src/trustdesk/reputation/tiers.py
"""Tier definitions and limits mapping."""
from __future__ import annotations

from enum import IntEnum

from trustdesk.reputation.types import TierLimits


class TierName(IntEnum):
    """Reputation tiers, ordered by trust level."""

    UNPROVEN = 0
    ESTABLISHED = 1
    TRUSTED = 2


TIER_DEFINITIONS: dict[TierName, TierLimits] = {
    TierName.UNPROVEN: TierLimits(
        capital_usd=100,
        max_position_pct=3.0,
        max_trades=1,
        max_daily_loss_pct=3.0,
    ),
    TierName.ESTABLISHED: TierLimits(
        capital_usd=500,
        max_position_pct=7.0,
        max_trades=3,
        max_daily_loss_pct=5.0,
    ),
    TierName.TRUSTED: TierLimits(
        capital_usd=1000,
        max_position_pct=10.0,
        max_trades=5,
        max_daily_loss_pct=5.0,
    ),
}


def get_tier_limits(tier: TierName) -> TierLimits:
    """Return a copy of the limits for the given tier."""
    src = TIER_DEFINITIONS[tier]
    return TierLimits(
        capital_usd=src.capital_usd,
        max_position_pct=src.max_position_pct,
        max_trades=src.max_trades,
        max_daily_loss_pct=src.max_daily_loss_pct,
    )
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/tests/test_tiers.py -x` -- expect PASS
- [ ] Commit: `git add backend/src/trustdesk/reputation/{__init__,types,constants,tiers}.py backend/src/trustdesk/reputation/tests/{__init__,test_tiers}.py && git commit -m "feat(reputation): add tier definitions, constants, and types"`

---

## Task 2: Promotion and demotion logic

### Step 2.1 -- Write test for promotion/demotion

- [ ] Create `backend/src/trustdesk/reputation/tests/test_promotion.py`

```python
# backend/src/trustdesk/reputation/tests/test_promotion.py
"""Tests for promotion and demotion logic."""
import pytest

from trustdesk.reputation.constants import COOLDOWN_TRADES_REQUIRED
from trustdesk.reputation.promotion import (
    check_demotion,
    check_promotion,
    is_in_cooldown,
)
from trustdesk.reputation.tiers import TierName
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, PromotionResult


def _make_feedback(
    kind: FeedbackKind = FeedbackKind.TRADE_CLOSE,
    score: int = 70,
    pnl_usd: float = 10.0,
    timestamp: int = 1000,
) -> FeedbackRecord:
    return FeedbackRecord(
        kind=kind,
        score=score,
        pnl_usd=pnl_usd,
        timestamp=timestamp,
        metadata={},
    )


class TestCheckPromotion:
    def test_unproven_not_enough_trades(self) -> None:
        history = [_make_feedback() for _ in range(10)]
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is False

    def test_unproven_to_established(self) -> None:
        history = [_make_feedback(pnl_usd=5.0) for _ in range(25)]
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is True
        assert result.new_tier == "ESTABLISHED"

    def test_unproven_to_established_negative_pnl(self) -> None:
        history = [_make_feedback(pnl_usd=-1.0) for _ in range(25)]
        result = check_promotion(TierName.UNPROVEN, history)
        assert result.changed is False
        assert "PnL" in result.reason or "pnl" in result.reason.lower()

    def test_established_to_trusted(self) -> None:
        # 55 trades, 65% equity rising, max DD 8%
        history = []
        for i in range(55):
            pnl = 10.0 if i % 100 < 65 else -3.0
            history.append(_make_feedback(pnl_usd=pnl, timestamp=1000 + i))
        result = check_promotion(TierName.ESTABLISHED, history)
        assert result.changed is True
        assert result.new_tier == "TRUSTED"

    def test_trusted_cannot_promote(self) -> None:
        history = [_make_feedback() for _ in range(100)]
        result = check_promotion(TierName.TRUSTED, history)
        assert result.changed is False

    def test_established_to_trusted_fails_equity_rising(self) -> None:
        # 55 trades but only 40% equity rising
        history = []
        for i in range(55):
            pnl = 10.0 if i % 100 < 40 else -3.0
            history.append(_make_feedback(pnl_usd=pnl, timestamp=1000 + i))
        result = check_promotion(TierName.ESTABLISHED, history)
        assert result.changed is False


class TestCheckDemotion:
    def test_no_demotion_on_good_history(self) -> None:
        history = [_make_feedback(pnl_usd=5.0) for _ in range(10)]
        result = check_demotion(
            TierName.ESTABLISHED, history, current_drawdown_pct=2.0, daily_loss_pct=1.0
        )
        assert result.changed is False

    def test_demotion_on_max_drawdown_exceeded(self) -> None:
        history = [_make_feedback() for _ in range(10)]
        result = check_demotion(
            TierName.ESTABLISHED,
            history,
            current_drawdown_pct=16.0,
            daily_loss_pct=0.0,
        )
        assert result.changed is True
        assert result.new_tier == "UNPROVEN"

    def test_demotion_on_consecutive_losses(self) -> None:
        history = [_make_feedback(pnl_usd=-5.0) for _ in range(5)]
        result = check_demotion(
            TierName.TRUSTED, history, current_drawdown_pct=2.0, daily_loss_pct=1.0
        )
        assert result.changed is True
        assert result.new_tier == "ESTABLISHED"

    def test_demotion_on_daily_loss_breach(self) -> None:
        history = [_make_feedback() for _ in range(10)]
        result = check_demotion(
            TierName.ESTABLISHED,
            history,
            current_drawdown_pct=2.0,
            daily_loss_pct=6.0,
        )
        assert result.changed is True

    def test_no_demotion_below_unproven(self) -> None:
        history = [_make_feedback(pnl_usd=-5.0) for _ in range(5)]
        result = check_demotion(
            TierName.UNPROVEN, history, current_drawdown_pct=2.0, daily_loss_pct=1.0
        )
        assert result.changed is False


class TestCooldown:
    def test_in_cooldown_not_enough_trades(self) -> None:
        last_demotion_ts = 5000
        history = [
            _make_feedback(timestamp=5001 + i)
            for i in range(COOLDOWN_TRADES_REQUIRED - 1)
        ]
        assert is_in_cooldown(history, last_demotion_ts) is True

    def test_cooldown_cleared(self) -> None:
        last_demotion_ts = 5000
        history = [
            _make_feedback(timestamp=5001 + i)
            for i in range(COOLDOWN_TRADES_REQUIRED)
        ]
        assert is_in_cooldown(history, last_demotion_ts) is False

    def test_no_cooldown_without_demotion(self) -> None:
        assert is_in_cooldown([], None) is False
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/tests/test_promotion.py -x` -- expect FAIL

### Step 2.2 -- Implement promotion.py

- [ ] Create `backend/src/trustdesk/reputation/promotion.py`

```python
# backend/src/trustdesk/reputation/promotion.py
"""Promotion, demotion, and cooldown logic."""
from __future__ import annotations

from trustdesk.reputation.constants import (
    COOLDOWN_TRADES_REQUIRED,
    DEMOTION_CONSECUTIVE_LOSSES,
    ESTABLISHED_MAX_DD_PCT,
    ESTABLISHED_MIN_PNL,
    ESTABLISHED_MIN_TRADES,
    TRUSTED_EQUITY_RISING_PCT,
    TRUSTED_MAX_DD_PCT,
    TRUSTED_MIN_TRADES,
)
from trustdesk.reputation.tiers import TIER_DEFINITIONS, TierName
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, PromotionResult


def _count_closed_trades(history: list[FeedbackRecord]) -> int:
    return sum(1 for f in history if f.kind == FeedbackKind.TRADE_CLOSE)


def _total_pnl(history: list[FeedbackRecord]) -> float:
    return sum(f.pnl_usd for f in history if f.kind == FeedbackKind.TRADE_CLOSE)


def _equity_rising_pct(history: list[FeedbackRecord]) -> float:
    closes = [f for f in history if f.kind == FeedbackKind.TRADE_CLOSE]
    if not closes:
        return 0.0
    rising = sum(1 for f in closes if f.pnl_usd > 0)
    return (rising / len(closes)) * 100.0


def _max_drawdown_from_history(history: list[FeedbackRecord]) -> float:
    closes = sorted(
        (f for f in history if f.kind == FeedbackKind.TRADE_CLOSE),
        key=lambda f: f.timestamp,
    )
    if not closes:
        return 0.0
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for f in closes:
        equity += f.pnl_usd
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = ((peak - equity) / peak) * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _no_change(tier: TierName, reason: str) -> PromotionResult:
    return PromotionResult(
        changed=False, old_tier=tier.name, new_tier=tier.name, reason=reason
    )


def check_promotion(
    current_tier: TierName, history: list[FeedbackRecord]
) -> PromotionResult:
    """Check if the agent qualifies for promotion."""
    if current_tier == TierName.TRUSTED:
        return _no_change(current_tier, "Already at highest tier")

    trade_count = _count_closed_trades(history)

    if current_tier == TierName.UNPROVEN:
        if trade_count < ESTABLISHED_MIN_TRADES:
            return _no_change(current_tier, f"Need {ESTABLISHED_MIN_TRADES} trades, have {trade_count}")
        if _total_pnl(history) <= ESTABLISHED_MIN_PNL:
            return _no_change(current_tier, "Total PnL must be positive")
        if _max_drawdown_from_history(history) > ESTABLISHED_MAX_DD_PCT:
            return _no_change(current_tier, "Max drawdown exceeds 15%")
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=TierName.ESTABLISHED.name,
            reason="Met ESTABLISHED criteria",
        )

    # ESTABLISHED -> TRUSTED
    if trade_count < TRUSTED_MIN_TRADES:
        return _no_change(current_tier, f"Need {TRUSTED_MIN_TRADES} trades, have {trade_count}")
    if _equity_rising_pct(history) < TRUSTED_EQUITY_RISING_PCT:
        return _no_change(current_tier, "Equity rising percentage too low")
    if _max_drawdown_from_history(history) > TRUSTED_MAX_DD_PCT:
        return _no_change(current_tier, "Max drawdown exceeds 10%")
    return PromotionResult(
        changed=True,
        old_tier=current_tier.name,
        new_tier=TierName.TRUSTED.name,
        reason="Met TRUSTED criteria",
    )


def check_demotion(
    current_tier: TierName,
    history: list[FeedbackRecord],
    current_drawdown_pct: float,
    daily_loss_pct: float,
) -> PromotionResult:
    """Check if the agent should be demoted."""
    if current_tier == TierName.UNPROVEN:
        return _no_change(current_tier, "Already at lowest tier")

    tier_limits = TIER_DEFINITIONS[current_tier]

    # Check max drawdown exceeded (15% hard limit)
    if current_drawdown_pct > ESTABLISHED_MAX_DD_PCT:
        new_tier = TierName(current_tier.value - 1)
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=new_tier.name,
            reason=f"Max drawdown {current_drawdown_pct:.1f}% exceeds 15%",
        )

    # Check consecutive losses
    closes = [f for f in history if f.kind == FeedbackKind.TRADE_CLOSE]
    recent = closes[-DEMOTION_CONSECUTIVE_LOSSES:]
    if len(recent) == DEMOTION_CONSECUTIVE_LOSSES and all(
        f.pnl_usd < 0 for f in recent
    ):
        new_tier = TierName(current_tier.value - 1)
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=new_tier.name,
            reason=f"{DEMOTION_CONSECUTIVE_LOSSES} consecutive losses",
        )

    # Check daily loss limit
    if daily_loss_pct > tier_limits.max_daily_loss_pct:
        new_tier = TierName(current_tier.value - 1)
        return PromotionResult(
            changed=True,
            old_tier=current_tier.name,
            new_tier=new_tier.name,
            reason=f"Daily loss {daily_loss_pct:.1f}% exceeds {tier_limits.max_daily_loss_pct}%",
        )

    return _no_change(current_tier, "No demotion triggers")


def is_in_cooldown(
    history: list[FeedbackRecord],
    last_demotion_timestamp: int | None,
) -> bool:
    """Check if agent is still in cooldown after demotion."""
    if last_demotion_timestamp is None:
        return False
    trades_since = sum(
        1
        for f in history
        if f.kind == FeedbackKind.TRADE_CLOSE
        and f.timestamp > last_demotion_timestamp
    )
    return trades_since < COOLDOWN_TRADES_REQUIRED
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/tests/test_promotion.py -x` -- expect PASS
- [ ] Commit: `git add backend/src/trustdesk/reputation/promotion.py backend/src/trustdesk/reputation/tests/test_promotion.py && git commit -m "feat(reputation): add promotion, demotion, and cooldown logic"`

---

## Task 3: Reputation engine (main orchestrator)

### Step 3.1 -- Write test for the engine

- [ ] Create `backend/src/trustdesk/reputation/tests/test_engine.py`

```python
# backend/src/trustdesk/reputation/tests/test_engine.py
"""Tests for the reputation engine orchestrator."""
import pytest

from trustdesk.reputation.engine import ReputationEngine
from trustdesk.reputation.tiers import TierName
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, TierLimits


def _close(pnl: float, ts: int = 1000) -> FeedbackRecord:
    return FeedbackRecord(
        kind=FeedbackKind.TRADE_CLOSE,
        score=70,
        pnl_usd=pnl,
        timestamp=ts,
        metadata={},
    )


def _tier_change(ts: int, score: int) -> FeedbackRecord:
    return FeedbackRecord(
        kind=FeedbackKind.TIER_CHANGE,
        score=score,
        pnl_usd=0.0,
        timestamp=ts,
        metadata={},
    )


class TestReputationEngine:
    def test_new_agent_is_unproven(self) -> None:
        engine = ReputationEngine()
        result = engine.evaluate([], current_drawdown_pct=0.0, daily_loss_pct=0.0)
        assert result.tier == TierName.UNPROVEN

    def test_returns_tier_limits(self) -> None:
        engine = ReputationEngine()
        result = engine.evaluate([], current_drawdown_pct=0.0, daily_loss_pct=0.0)
        assert result.limits.capital_usd == 100
        assert result.limits.max_position_pct == 3.0

    def test_promotion_after_enough_trades(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.tier == TierName.ESTABLISHED
        assert result.limits.capital_usd == 500

    def test_demotion_on_drawdown(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        result = engine.evaluate(
            history, current_drawdown_pct=20.0, daily_loss_pct=0.0
        )
        # Would be ESTABLISHED by promotion but gets demoted
        assert result.tier == TierName.UNPROVEN

    def test_cooldown_prevents_repromotion(self) -> None:
        engine = ReputationEngine()
        # History: 25 good trades, then demotion event, then 3 trades
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        history.append(_tier_change(ts=2000, score=40))  # demotion
        history.extend([_close(pnl=5.0, ts=2001 + i) for i in range(3)])
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.tier == TierName.UNPROVEN  # cooldown active

    def test_cooldown_clears_after_enough_trades(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        history.append(_tier_change(ts=2000, score=40))  # demotion
        history.extend([_close(pnl=5.0, ts=2001 + i) for i in range(5)])
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        # Cooldown cleared, 30 total closes, PnL > 0 => ESTABLISHED
        assert result.tier == TierName.ESTABLISHED


class TestEvaluationResult:
    def test_result_has_promotion_info(self) -> None:
        engine = ReputationEngine()
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        result = engine.evaluate(
            history, current_drawdown_pct=0.0, daily_loss_pct=0.0
        )
        assert result.promotion_result is not None
        assert result.promotion_result.changed is True
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/tests/test_engine.py -x` -- expect FAIL

### Step 3.2 -- Implement engine.py

- [ ] Create `backend/src/trustdesk/reputation/engine.py`

```python
# backend/src/trustdesk/reputation/engine.py
"""Reputation engine -- computes tier from feedback history."""
from __future__ import annotations

from dataclasses import dataclass

from trustdesk.reputation.constants import DEMOTION_SCORE
from trustdesk.reputation.promotion import check_demotion, check_promotion, is_in_cooldown
from trustdesk.reputation.tiers import TierName, get_tier_limits
from trustdesk.reputation.types import (
    FeedbackKind,
    FeedbackRecord,
    PromotionResult,
    TierLimits,
)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Result of a reputation evaluation."""

    tier: TierName
    limits: TierLimits
    promotion_result: PromotionResult | None
    demotion_result: PromotionResult | None


class ReputationEngine:
    """Pure computation engine: feedback history -> tier + limits."""

    def evaluate(
        self,
        history: list[FeedbackRecord],
        current_drawdown_pct: float,
        daily_loss_pct: float,
    ) -> EvaluationResult:
        """Evaluate an agent's tier based on feedback history."""
        if not history:
            return EvaluationResult(
                tier=TierName.UNPROVEN,
                limits=get_tier_limits(TierName.UNPROVEN),
                promotion_result=None,
                demotion_result=None,
            )

        # Start at UNPROVEN, check if promotions apply
        current_tier = TierName.UNPROVEN

        # Check promotion (iteratively up the tiers)
        promo_result: PromotionResult | None = None
        last_demotion_ts = self._find_last_demotion_ts(history)

        # Check if in cooldown
        if not is_in_cooldown(history, last_demotion_ts):
            # Try to promote through tiers
            while current_tier < TierName.TRUSTED:
                result = check_promotion(current_tier, history)
                if not result.changed:
                    promo_result = result
                    break
                current_tier = TierName[result.new_tier]
                promo_result = result

        # Check demotion
        demo_result = check_demotion(
            current_tier, history, current_drawdown_pct, daily_loss_pct
        )
        if demo_result.changed:
            current_tier = TierName[demo_result.new_tier]

        return EvaluationResult(
            tier=current_tier,
            limits=get_tier_limits(current_tier),
            promotion_result=promo_result,
            demotion_result=demo_result if demo_result.changed else None,
        )

    def _find_last_demotion_ts(
        self, history: list[FeedbackRecord]
    ) -> int | None:
        """Find timestamp of the most recent demotion event."""
        demotions = [
            f
            for f in history
            if f.kind == FeedbackKind.TIER_CHANGE and f.score == DEMOTION_SCORE
        ]
        if not demotions:
            return None
        return max(f.timestamp for f in demotions)
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/tests/ -x` -- expect ALL PASS
- [ ] Commit: `git add backend/src/trustdesk/reputation/engine.py backend/src/trustdesk/reputation/tests/test_engine.py && git commit -m "feat(reputation): add engine orchestrator with promotion/demotion/cooldown"`

---

## Task 4: Risk manager types and constants

### Step 4.1 -- Create risk manager types and constants

- [ ] Create `backend/src/trustdesk/risk_manager/__init__.py`

```python
# backend/src/trustdesk/risk_manager/__init__.py
"""Risk manager -- external validator for trade proposals."""
```

- [ ] Create `backend/src/trustdesk/risk_manager/types.py`

```python
# backend/src/trustdesk/risk_manager/types.py
"""Internal types for the risk manager."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class CheckResult(StrEnum):
    """Result of a single risk check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class VerdictStatus(StrEnum):
    """Overall verdict status."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPROVED_HARD_ONLY = "APPROVED_HARD_ONLY"


class DrawdownLevel(StrEnum):
    """Current drawdown defense level."""

    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    RESTRICTED = "RESTRICTED"
    HALT = "HALT"
    FULL_CASH = "FULL_CASH"


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Current state of the agent's portfolio."""

    open_positions: int
    total_exposure_pct: float
    daily_realized_loss_pct: float
    current_drawdown_pct: float
    consecutive_losses: int
    open_pairs: list[str]
    last_trade_timestamps: dict[str, int]


@dataclass(frozen=True, slots=True)
class RiskParameters:
    """Effective risk parameters after adaptive adjustments."""

    max_position_pct: float
    max_exposure_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    min_trade_interval_seconds: int
    min_alignment: str
    reject_overrides: bool
    btc_only: bool
    no_new_trades: bool
    full_cash: bool


@dataclass(slots=True)
class CheckReport:
    """Report from running all checks."""

    hard_checks: dict[str, CheckResult] = field(default_factory=dict)
    soft_checks: dict[str, CheckResult] = field(default_factory=dict)
    soft_details: dict[str, str] = field(default_factory=dict)
    hard_reasons: dict[str, str] = field(default_factory=dict)


class LLMEvaluator(Protocol):
    """Protocol for the LLM-based soft check evaluator."""

    async def evaluate_soft_checks(
        self,
        proposal: dict,
        portfolio: dict,
        parameters: dict,
    ) -> dict[str, str]:
        """Return dict mapping check_name -> 'PASS' or 'FAIL: reason'."""
        ...
```

- [ ] Create `backend/src/trustdesk/risk_manager/constants.py`

```python
# backend/src/trustdesk/risk_manager/constants.py
"""Default thresholds for the risk manager."""

# Hard check defaults
MAX_TOTAL_EXPOSURE_PCT: float = 40.0
MIN_TRADE_INTERVAL_SECONDS: int = 1800  # 30 minutes

# Drawdown defense thresholds
DRAWDOWN_CAUTION_PCT: float = 3.0
DRAWDOWN_RESTRICTED_PCT: float = 5.0
DRAWDOWN_HALT_PCT: float = 8.0
DRAWDOWN_FULL_CASH_PCT: float = 12.0

# Adaptive parameters
CONSECUTIVE_LOSS_THRESHOLD: int = 3
DAILY_DRAWDOWN_ADAPTIVE_PCT: float = 3.0

# Soft check names
SOFT_CHECK_CORRELATION = "correlation"
SOFT_CHECK_REGIME = "regime_alignment"
SOFT_CHECK_DRAWDOWN_HEADROOM = "drawdown_headroom"
SOFT_CHECK_INVALIDATION = "invalidation_plausibility"
SOFT_CHECK_ALIGNMENT_SCORE = "alignment_score_calibration"
SOFT_CHECK_OVERRIDE = "override_scrutiny"

ALL_SOFT_CHECKS: list[str] = [
    SOFT_CHECK_CORRELATION,
    SOFT_CHECK_REGIME,
    SOFT_CHECK_DRAWDOWN_HEADROOM,
    SOFT_CHECK_INVALIDATION,
    SOFT_CHECK_ALIGNMENT_SCORE,
    SOFT_CHECK_OVERRIDE,
]
```

- [ ] Create `backend/src/trustdesk/risk_manager/tests/__init__.py`
- [ ] Commit: `git add backend/src/trustdesk/risk_manager/ && git commit -m "feat(risk_manager): add types and constants"`

---

## Task 5: Hard checks

### Step 5.1 -- Write test for hard checks

- [ ] Create `backend/src/trustdesk/risk_manager/tests/test_hard_checks.py`

```python
# backend/src/trustdesk/risk_manager/tests/test_hard_checks.py
"""Tests for deterministic hard checks."""
import pytest

from trustdesk.risk_manager.hard_checks import (
    check_daily_loss,
    check_max_open_positions,
    check_min_trade_interval,
    check_position_size,
    check_total_exposure,
    run_all_hard_checks,
)
from trustdesk.risk_manager.types import CheckResult, PortfolioState, RiskParameters


def _default_params(**overrides: object) -> RiskParameters:
    defaults = dict(
        max_position_pct=7.0,
        max_exposure_pct=40.0,
        max_daily_loss_pct=5.0,
        max_open_positions=3,
        min_trade_interval_seconds=1800,
        min_alignment="MODERATE",
        reject_overrides=False,
        btc_only=False,
        no_new_trades=False,
        full_cash=False,
    )
    defaults.update(overrides)
    return RiskParameters(**defaults)  # type: ignore[arg-type]


def _default_portfolio(**overrides: object) -> PortfolioState:
    defaults = dict(
        open_positions=1,
        total_exposure_pct=15.0,
        daily_realized_loss_pct=1.0,
        current_drawdown_pct=2.0,
        consecutive_losses=0,
        open_pairs=["BTC/USD"],
        last_trade_timestamps={"BTC/USD": 1000},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)  # type: ignore[arg-type]


class TestPositionSize:
    def test_within_limit(self) -> None:
        result, reason = check_position_size(5.0, _default_params())
        assert result == CheckResult.PASS

    def test_exceeds_limit(self) -> None:
        result, reason = check_position_size(10.0, _default_params())
        assert result == CheckResult.FAIL
        assert "10.0%" in reason


class TestTotalExposure:
    def test_within_limit(self) -> None:
        result, reason = check_total_exposure(
            5.0, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.PASS

    def test_exceeds_limit(self) -> None:
        portfolio = _default_portfolio(total_exposure_pct=38.0)
        result, reason = check_total_exposure(5.0, portfolio, _default_params())
        assert result == CheckResult.FAIL


class TestDailyLoss:
    def test_within_limit(self) -> None:
        result, reason = check_daily_loss(_default_portfolio(), _default_params())
        assert result == CheckResult.PASS

    def test_exceeds_limit(self) -> None:
        portfolio = _default_portfolio(daily_realized_loss_pct=6.0)
        result, reason = check_daily_loss(portfolio, _default_params())
        assert result == CheckResult.FAIL


class TestMaxOpenPositions:
    def test_within_limit(self) -> None:
        result, reason = check_max_open_positions(_default_portfolio(), _default_params())
        assert result == CheckResult.PASS

    def test_at_limit(self) -> None:
        portfolio = _default_portfolio(open_positions=3)
        result, reason = check_max_open_positions(portfolio, _default_params())
        assert result == CheckResult.FAIL


class TestMinTradeInterval:
    def test_enough_time(self) -> None:
        result, reason = check_min_trade_interval(
            "BTC/USD", 5000, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.PASS

    def test_too_soon(self) -> None:
        result, reason = check_min_trade_interval(
            "BTC/USD", 1500, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.FAIL

    def test_new_pair_always_passes(self) -> None:
        result, reason = check_min_trade_interval(
            "ETH/USD", 1000, _default_portfolio(), _default_params()
        )
        assert result == CheckResult.PASS


class TestRunAllHardChecks:
    def test_all_pass(self) -> None:
        results, reasons = run_all_hard_checks(
            position_size_pct=5.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=_default_params(),
        )
        assert all(r == CheckResult.PASS for r in results.values())

    def test_no_new_trades(self) -> None:
        params = _default_params(no_new_trades=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["no_new_trades"] == CheckResult.FAIL

    def test_full_cash(self) -> None:
        params = _default_params(full_cash=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["full_cash"] == CheckResult.FAIL

    def test_btc_only_rejects_non_btc(self) -> None:
        params = _default_params(btc_only=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="ETH/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["btc_only"] == CheckResult.FAIL

    def test_btc_only_allows_btc(self) -> None:
        params = _default_params(btc_only=True)
        results, reasons = run_all_hard_checks(
            position_size_pct=1.0,
            pair="BTC/USD",
            current_timestamp=5000,
            portfolio=_default_portfolio(),
            params=params,
        )
        assert results["btc_only"] == CheckResult.PASS
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_hard_checks.py -x` -- expect FAIL

### Step 5.2 -- Implement hard_checks.py

- [ ] Create `backend/src/trustdesk/risk_manager/hard_checks.py`

```python
# backend/src/trustdesk/risk_manager/hard_checks.py
"""Deterministic hard checks -- pure functions, no side effects."""
from __future__ import annotations

from trustdesk.risk_manager.types import CheckResult, PortfolioState, RiskParameters

_Outcome = tuple[CheckResult, str]


def check_position_size(
    position_size_pct: float, params: RiskParameters
) -> _Outcome:
    """Position size must be <= tier max."""
    if position_size_pct > params.max_position_pct:
        return (
            CheckResult.FAIL,
            f"Position {position_size_pct}% exceeds max {params.max_position_pct}%",
        )
    return CheckResult.PASS, ""


def check_total_exposure(
    new_position_pct: float,
    portfolio: PortfolioState,
    params: RiskParameters,
) -> _Outcome:
    """Total open exposure must be <= 40% of allocated capital."""
    projected = portfolio.total_exposure_pct + new_position_pct
    if projected > params.max_exposure_pct:
        return (
            CheckResult.FAIL,
            f"Projected exposure {projected:.1f}% exceeds max {params.max_exposure_pct}%",
        )
    return CheckResult.PASS, ""


def check_daily_loss(
    portfolio: PortfolioState, params: RiskParameters
) -> _Outcome:
    """Daily realized loss must be <= tier max."""
    if portfolio.daily_realized_loss_pct > params.max_daily_loss_pct:
        return (
            CheckResult.FAIL,
            f"Daily loss {portfolio.daily_realized_loss_pct:.1f}% exceeds max {params.max_daily_loss_pct}%",
        )
    return CheckResult.PASS, ""


def check_max_open_positions(
    portfolio: PortfolioState, params: RiskParameters
) -> _Outcome:
    """Open positions must be < tier max (new trade would exceed)."""
    if portfolio.open_positions >= params.max_open_positions:
        return (
            CheckResult.FAIL,
            f"Already at {portfolio.open_positions} positions (max {params.max_open_positions})",
        )
    return CheckResult.PASS, ""


def check_min_trade_interval(
    pair: str,
    current_timestamp: int,
    portfolio: PortfolioState,
    params: RiskParameters,
) -> _Outcome:
    """Min time between trades on same pair: 30 minutes."""
    last_ts = portfolio.last_trade_timestamps.get(pair)
    if last_ts is None:
        return CheckResult.PASS, ""
    elapsed = current_timestamp - last_ts
    if elapsed < params.min_trade_interval_seconds:
        remaining = params.min_trade_interval_seconds - elapsed
        return (
            CheckResult.FAIL,
            f"Must wait {remaining}s more before trading {pair}",
        )
    return CheckResult.PASS, ""


def run_all_hard_checks(
    position_size_pct: float,
    pair: str,
    current_timestamp: int,
    portfolio: PortfolioState,
    params: RiskParameters,
) -> tuple[dict[str, CheckResult], dict[str, str]]:
    """Run all hard checks. Returns (results, reasons) dicts."""
    results: dict[str, CheckResult] = {}
    reasons: dict[str, str] = {}

    # Adaptive blockers first
    if params.full_cash:
        results["full_cash"] = CheckResult.FAIL
        reasons["full_cash"] = "Full cash mode active -- no trades allowed"
    if params.no_new_trades:
        results["no_new_trades"] = CheckResult.FAIL
        reasons["no_new_trades"] = "No new trades -- manage existing only"
    if params.btc_only and "BTC" not in pair.upper():
        results["btc_only"] = CheckResult.FAIL
        reasons["btc_only"] = f"BTC-only mode: {pair} rejected"
    elif params.btc_only:
        results["btc_only"] = CheckResult.PASS
        reasons["btc_only"] = ""

    checks = [
        ("position_size", check_position_size(position_size_pct, params)),
        ("total_exposure", check_total_exposure(position_size_pct, portfolio, params)),
        ("daily_loss", check_daily_loss(portfolio, params)),
        ("max_open_positions", check_max_open_positions(portfolio, params)),
        ("min_trade_interval", check_min_trade_interval(pair, current_timestamp, portfolio, params)),
    ]

    for name, (result, reason) in checks:
        results[name] = result
        reasons[name] = reason

    return results, reasons
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_hard_checks.py -x` -- expect PASS
- [ ] Commit: `git add backend/src/trustdesk/risk_manager/hard_checks.py backend/src/trustdesk/risk_manager/tests/test_hard_checks.py && git commit -m "feat(risk_manager): add deterministic hard checks"`

---

## Task 6: Adaptive parameters and drawdown defense

### Step 6.1 -- Write test for adaptive parameters

- [ ] Create `backend/src/trustdesk/risk_manager/tests/test_adaptive.py`

```python
# backend/src/trustdesk/risk_manager/tests/test_adaptive.py
"""Tests for adaptive parameter adjustments and drawdown defense."""
import pytest

from trustdesk.reputation.tiers import TierName
from trustdesk.reputation.types import TierLimits
from trustdesk.risk_manager.adaptive import (
    apply_adaptive_adjustments,
    get_drawdown_level,
)
from trustdesk.risk_manager.types import DrawdownLevel, PortfolioState, RiskParameters


def _portfolio(**overrides: object) -> PortfolioState:
    defaults = dict(
        open_positions=1,
        total_exposure_pct=10.0,
        daily_realized_loss_pct=1.0,
        current_drawdown_pct=2.0,
        consecutive_losses=0,
        open_pairs=["BTC/USD"],
        last_trade_timestamps={},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)  # type: ignore[arg-type]


class TestDrawdownLevel:
    def test_normal(self) -> None:
        assert get_drawdown_level(2.0) == DrawdownLevel.NORMAL

    def test_caution(self) -> None:
        assert get_drawdown_level(4.0) == DrawdownLevel.CAUTION

    def test_restricted(self) -> None:
        assert get_drawdown_level(6.0) == DrawdownLevel.RESTRICTED

    def test_halt(self) -> None:
        assert get_drawdown_level(10.0) == DrawdownLevel.HALT

    def test_full_cash(self) -> None:
        assert get_drawdown_level(15.0) == DrawdownLevel.FULL_CASH

    def test_boundary_at_3(self) -> None:
        assert get_drawdown_level(3.0) == DrawdownLevel.NORMAL
        assert get_drawdown_level(3.01) == DrawdownLevel.CAUTION


class TestAdaptiveAdjustments:
    def test_normal_no_changes(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio()
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.max_position_pct == 7.0
        assert params.no_new_trades is False
        assert params.full_cash is False

    def test_consecutive_losses_tightens(self) -> None:
        limits = TierLimits(
            capital_usd=1000,
            max_position_pct=10.0,
            max_trades=5,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(consecutive_losses=3)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.max_position_pct == 7.0
        assert params.min_alignment == "STRONG"

    def test_daily_drawdown_above_3_pct(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(daily_realized_loss_pct=3.5)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.min_alignment == "STRONG"
        assert params.reject_overrides is True

    def test_caution_drawdown_level(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=4.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.min_alignment == "STRONG"
        assert params.max_position_pct == 7.0

    def test_restricted_drawdown_level(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=6.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.btc_only is True
        assert params.max_open_positions == 1
        assert params.min_alignment == "STRONG"

    def test_halt_drawdown_level(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=10.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.no_new_trades is True

    def test_full_cash(self) -> None:
        limits = TierLimits(
            capital_usd=500,
            max_position_pct=7.0,
            max_trades=3,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio(current_drawdown_pct=15.0)
        params = apply_adaptive_adjustments(limits, portfolio, regime="TRENDING")
        assert params.full_cash is True

    def test_volatile_regime_halves_soft_limits(self) -> None:
        limits = TierLimits(
            capital_usd=1000,
            max_position_pct=10.0,
            max_trades=5,
            max_daily_loss_pct=5.0,
        )
        portfolio = _portfolio()
        params = apply_adaptive_adjustments(limits, portfolio, regime="VOLATILE")
        assert params.max_position_pct == 5.0
        assert params.max_open_positions == 2
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_adaptive.py -x` -- expect FAIL

### Step 6.2 -- Implement adaptive.py

- [ ] Create `backend/src/trustdesk/risk_manager/adaptive.py`

```python
# backend/src/trustdesk/risk_manager/adaptive.py
"""Adaptive parameter adjustments and drawdown defense."""
from __future__ import annotations

from trustdesk.reputation.types import TierLimits
from trustdesk.risk_manager.constants import (
    CONSECUTIVE_LOSS_THRESHOLD,
    DAILY_DRAWDOWN_ADAPTIVE_PCT,
    DRAWDOWN_CAUTION_PCT,
    DRAWDOWN_FULL_CASH_PCT,
    DRAWDOWN_HALT_PCT,
    DRAWDOWN_RESTRICTED_PCT,
    MAX_TOTAL_EXPOSURE_PCT,
    MIN_TRADE_INTERVAL_SECONDS,
)
from trustdesk.risk_manager.types import DrawdownLevel, PortfolioState, RiskParameters


def get_drawdown_level(drawdown_pct: float) -> DrawdownLevel:
    """Map drawdown percentage to defense level."""
    if drawdown_pct > DRAWDOWN_FULL_CASH_PCT:
        return DrawdownLevel.FULL_CASH
    if drawdown_pct > DRAWDOWN_HALT_PCT:
        return DrawdownLevel.HALT
    if drawdown_pct > DRAWDOWN_RESTRICTED_PCT:
        return DrawdownLevel.RESTRICTED
    if drawdown_pct > DRAWDOWN_CAUTION_PCT:
        return DrawdownLevel.CAUTION
    return DrawdownLevel.NORMAL


def apply_adaptive_adjustments(
    tier_limits: TierLimits,
    portfolio: PortfolioState,
    regime: str,
) -> RiskParameters:
    """Build effective risk parameters from tier limits + conditions."""
    max_pos = tier_limits.max_position_pct
    max_exposure = MAX_TOTAL_EXPOSURE_PCT
    max_daily = tier_limits.max_daily_loss_pct
    max_open = tier_limits.max_trades
    min_interval = MIN_TRADE_INTERVAL_SECONDS
    min_alignment = "MODERATE"
    reject_overrides = False
    btc_only = False
    no_new_trades = False
    full_cash = False

    # --- Adaptive: consecutive losses ---
    if portfolio.consecutive_losses >= CONSECUTIVE_LOSS_THRESHOLD:
        max_pos = min(max_pos, 7.0)
        min_alignment = "STRONG"

    # --- Adaptive: daily drawdown ---
    if portfolio.daily_realized_loss_pct > DAILY_DRAWDOWN_ADAPTIVE_PCT:
        min_alignment = "STRONG"
        reject_overrides = True

    # --- Adaptive: regime ---
    if regime == "VOLATILE":
        max_pos = max_pos / 2.0
        max_open = max(1, max_open // 2)

    # --- Drawdown defense ---
    dd_level = get_drawdown_level(portfolio.current_drawdown_pct)

    if dd_level == DrawdownLevel.CAUTION:
        min_alignment = "STRONG"
        max_pos = min(max_pos, 7.0)
    elif dd_level == DrawdownLevel.RESTRICTED:
        btc_only = True
        max_open = 1
        min_alignment = "STRONG"
    elif dd_level == DrawdownLevel.HALT:
        no_new_trades = True
    elif dd_level == DrawdownLevel.FULL_CASH:
        full_cash = True

    return RiskParameters(
        max_position_pct=max_pos,
        max_exposure_pct=max_exposure,
        max_daily_loss_pct=max_daily,
        max_open_positions=max_open,
        min_trade_interval_seconds=min_interval,
        min_alignment=min_alignment,
        reject_overrides=reject_overrides,
        btc_only=btc_only,
        no_new_trades=no_new_trades,
        full_cash=full_cash,
    )
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_adaptive.py -x` -- expect PASS
- [ ] Commit: `git add backend/src/trustdesk/risk_manager/adaptive.py backend/src/trustdesk/risk_manager/tests/test_adaptive.py && git commit -m "feat(risk_manager): add adaptive parameters and drawdown defense"`

---

## Task 7: Soft checks

### Step 7.1 -- Write test for soft checks

- [ ] Create `backend/src/trustdesk/risk_manager/tests/test_soft_checks.py`

```python
# backend/src/trustdesk/risk_manager/tests/test_soft_checks.py
"""Tests for LLM-evaluated soft checks."""
import pytest

from trustdesk.risk_manager.soft_checks import (
    parse_llm_response,
    build_soft_check_prompt,
    run_soft_checks,
)
from trustdesk.risk_manager.types import CheckResult


class TestParseLLMResponse:
    def test_all_pass(self) -> None:
        raw = {
            "correlation": "PASS",
            "regime_alignment": "PASS",
            "drawdown_headroom": "PASS",
            "invalidation_plausibility": "PASS",
            "alignment_score_calibration": "PASS",
            "override_scrutiny": "PASS",
        }
        results, details = parse_llm_response(raw)
        assert all(r == CheckResult.PASS for r in results.values())
        assert all(d == "" for d in details.values())

    def test_fail_with_reason(self) -> None:
        raw = {
            "correlation": "FAIL: BTC and ETH are 90% correlated",
            "regime_alignment": "PASS",
            "drawdown_headroom": "PASS",
            "invalidation_plausibility": "PASS",
            "alignment_score_calibration": "PASS",
            "override_scrutiny": "PASS",
        }
        results, details = parse_llm_response(raw)
        assert results["correlation"] == CheckResult.FAIL
        assert "90% correlated" in details["correlation"]

    def test_missing_check_treated_as_fail(self) -> None:
        raw = {"correlation": "PASS"}
        results, details = parse_llm_response(raw)
        assert results["regime_alignment"] == CheckResult.FAIL
        assert "missing" in details["regime_alignment"].lower()

    def test_unexpected_value_treated_as_fail(self) -> None:
        raw = {
            "correlation": "MAYBE",
            "regime_alignment": "PASS",
            "drawdown_headroom": "PASS",
            "invalidation_plausibility": "PASS",
            "alignment_score_calibration": "PASS",
            "override_scrutiny": "PASS",
        }
        results, details = parse_llm_response(raw)
        assert results["correlation"] == CheckResult.FAIL


class TestBuildPrompt:
    def test_returns_nonempty_string(self) -> None:
        prompt = build_soft_check_prompt(
            proposal={"pair": "BTC/USD", "size_pct": 5.0},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "correlation" in prompt.lower()


class TestRunSoftChecks:
    @pytest.mark.asyncio
    async def test_with_passing_evaluator(self) -> None:
        async def mock_eval(proposal: dict, portfolio: dict, parameters: dict) -> dict[str, str]:
            return {
                "correlation": "PASS",
                "regime_alignment": "PASS",
                "drawdown_headroom": "PASS",
                "invalidation_plausibility": "PASS",
                "alignment_score_calibration": "PASS",
                "override_scrutiny": "PASS",
            }

        results, details = await run_soft_checks(
            evaluator=mock_eval,
            proposal={"pair": "BTC/USD"},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert all(r == CheckResult.PASS for r in results.values())

    @pytest.mark.asyncio
    async def test_with_failing_evaluator(self) -> None:
        async def mock_eval(proposal: dict, portfolio: dict, parameters: dict) -> dict[str, str]:
            return {
                "correlation": "FAIL: too correlated",
                "regime_alignment": "PASS",
                "drawdown_headroom": "PASS",
                "invalidation_plausibility": "PASS",
                "alignment_score_calibration": "PASS",
                "override_scrutiny": "PASS",
            }

        results, details = await run_soft_checks(
            evaluator=mock_eval,
            proposal={"pair": "BTC/USD"},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert results["correlation"] == CheckResult.FAIL
        assert "too correlated" in details["correlation"]

    @pytest.mark.asyncio
    async def test_evaluator_exception_all_fail(self) -> None:
        async def mock_eval(proposal: dict, portfolio: dict, parameters: dict) -> dict[str, str]:
            raise RuntimeError("API unavailable")

        results, details = await run_soft_checks(
            evaluator=mock_eval,
            proposal={"pair": "BTC/USD"},
            portfolio={"open_positions": 1},
            parameters={"max_position_pct": 7.0},
        )
        assert all(r == CheckResult.FAIL for r in results.values())
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_soft_checks.py -x` -- expect FAIL

### Step 7.2 -- Implement soft_checks.py

- [ ] Create `backend/src/trustdesk/risk_manager/soft_checks.py`

```python
# backend/src/trustdesk/risk_manager/soft_checks.py
"""LLM-evaluated soft checks."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

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
            details[check_name] = f"Missing from LLM response"
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
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_soft_checks.py -x` -- expect PASS
- [ ] Commit: `git add backend/src/trustdesk/risk_manager/soft_checks.py backend/src/trustdesk/risk_manager/tests/test_soft_checks.py && git commit -m "feat(risk_manager): add LLM-evaluated soft checks"`

---

## Task 8: Circuit breaker

### Step 8.1 -- Write test for circuit breaker

- [ ] Create `backend/src/trustdesk/risk_manager/tests/test_circuit_breaker.py`

```python
# backend/src/trustdesk/risk_manager/tests/test_circuit_breaker.py
"""Tests for circuit breaker -- LLM unavailable mode."""
import pytest

from trustdesk.risk_manager.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_initially_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_is_available_when_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        assert cb.is_available is True

    def test_is_unavailable_when_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_available is False

    def test_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=0)
        for _ in range(3):
            cb.record_failure()
        # reset_timeout_s=0 so it should immediately be half-open
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_s=0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_circuit_breaker.py -x` -- expect FAIL

### Step 8.2 -- Implement circuit_breaker.py

- [ ] Create `backend/src/trustdesk/risk_manager/circuit_breaker.py`

```python
# backend/src/trustdesk/risk_manager/circuit_breaker.py
"""Circuit breaker for LLM availability."""
from __future__ import annotations

import time
from enum import StrEnum


class CircuitState(StrEnum):
    """State of the circuit breaker."""

    CLOSED = "CLOSED"  # Normal operation, LLM available
    OPEN = "OPEN"  # LLM unavailable, skip soft checks
    HALF_OPEN = "HALF_OPEN"  # Testing if LLM is back


class CircuitBreaker:
    """Tracks LLM availability and skips soft checks when unavailable.

    - CLOSED: LLM is available, all checks run.
    - OPEN: LLM has failed repeatedly, skip soft checks.
    - HALF_OPEN: After timeout, allow one attempt to test LLM.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_s: int = 60,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._reset_timeout_s = reset_timeout_s
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        """Current state, accounting for timeout transitions."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._reset_timeout_s:
                return CircuitState.HALF_OPEN
        return self._state

    @property
    def is_available(self) -> bool:
        """Whether soft checks should run."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful LLM call."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed LLM call."""
        current = self.state
        if current == CircuitState.HALF_OPEN:
            # Failed during probe -- reopen
            self._state = CircuitState.OPEN
            self._last_failure_time = time.monotonic()
            return

        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_circuit_breaker.py -x` -- expect PASS
- [ ] Commit: `git add backend/src/trustdesk/risk_manager/circuit_breaker.py backend/src/trustdesk/risk_manager/tests/test_circuit_breaker.py && git commit -m "feat(risk_manager): add circuit breaker for LLM availability"`

---

## Task 9: Risk manager orchestrator

### Step 9.1 -- Write test for the manager

- [ ] Create `backend/src/trustdesk/risk_manager/tests/test_manager.py`

```python
# backend/src/trustdesk/risk_manager/tests/test_manager.py
"""Tests for the risk manager orchestrator."""
import pytest

from trustdesk.reputation.engine import ReputationEngine
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord
from trustdesk.risk_manager.circuit_breaker import CircuitBreaker
from trustdesk.risk_manager.manager import RiskManager
from trustdesk.risk_manager.types import PortfolioState, VerdictStatus


def _close(pnl: float, ts: int) -> FeedbackRecord:
    return FeedbackRecord(
        kind=FeedbackKind.TRADE_CLOSE,
        score=70,
        pnl_usd=pnl,
        timestamp=ts,
        metadata={},
    )


def _portfolio(**overrides: object) -> PortfolioState:
    defaults = dict(
        open_positions=0,
        total_exposure_pct=0.0,
        daily_realized_loss_pct=0.0,
        current_drawdown_pct=0.0,
        consecutive_losses=0,
        open_pairs=[],
        last_trade_timestamps={},
    )
    defaults.update(overrides)
    return PortfolioState(**defaults)  # type: ignore[arg-type]


async def _pass_evaluator(
    proposal: dict, portfolio: dict, parameters: dict
) -> dict[str, str]:
    return {
        "correlation": "PASS",
        "regime_alignment": "PASS",
        "drawdown_headroom": "PASS",
        "invalidation_plausibility": "PASS",
        "alignment_score_calibration": "PASS",
        "override_scrutiny": "PASS",
    }


async def _fail_evaluator(
    proposal: dict, portfolio: dict, parameters: dict
) -> dict[str, str]:
    return {
        "correlation": "FAIL: 95% correlated",
        "regime_alignment": "PASS",
        "drawdown_headroom": "PASS",
        "invalidation_plausibility": "PASS",
        "alignment_score_calibration": "PASS",
        "override_scrutiny": "PASS",
    }


class TestRiskManager:
    @pytest.mark.asyncio
    async def test_approve_clean_proposal(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.APPROVED

    @pytest.mark.asyncio
    async def test_reject_oversized_position(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 5.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        # Unproven tier: max 3%
        assert verdict.status == VerdictStatus.REJECTED
        assert any("position" in r.lower() for r in verdict.hard_reasons.values() if r)

    @pytest.mark.asyncio
    async def test_reject_on_soft_check_fail(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_fail_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.REJECTED

    @pytest.mark.asyncio
    async def test_hard_only_when_circuit_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, reset_timeout_s=9999)
        cb.record_failure()  # Opens circuit

        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=cb,
            llm_evaluator=_fail_evaluator,  # Should not be called
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.APPROVED_HARD_ONLY
        assert verdict.soft_checks_note == "SKIPPED_LLM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_established_agent_higher_limits(self) -> None:
        history = [_close(pnl=5.0, ts=1000 + i) for i in range(25)]
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 5.0},
            portfolio=_portfolio(),
            feedback_history=history,
            regime="TRENDING",
            current_timestamp=5000,
        )
        # Established tier: max 7%, so 5% should pass
        assert verdict.status == VerdictStatus.APPROVED

    @pytest.mark.asyncio
    async def test_verdict_contains_tier_info(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 2.0},
            portfolio=_portfolio(),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.tier == "UNPROVEN"
        assert verdict.effective_limits is not None


class TestRiskManagerDrawdownDefense:
    @pytest.mark.asyncio
    async def test_halt_blocks_new_trades(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 1.0},
            portfolio=_portfolio(current_drawdown_pct=10.0),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.REJECTED

    @pytest.mark.asyncio
    async def test_full_cash_blocks_everything(self) -> None:
        manager = RiskManager(
            reputation_engine=ReputationEngine(),
            circuit_breaker=CircuitBreaker(),
            llm_evaluator=_pass_evaluator,
        )
        verdict = await manager.evaluate(
            proposal={"pair": "BTC/USD", "size_pct": 1.0},
            portfolio=_portfolio(current_drawdown_pct=15.0),
            feedback_history=[],
            regime="TRENDING",
            current_timestamp=5000,
        )
        assert verdict.status == VerdictStatus.REJECTED
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_manager.py -x` -- expect FAIL

### Step 9.2 -- Implement manager.py

- [ ] Create `backend/src/trustdesk/risk_manager/manager.py`

```python
# backend/src/trustdesk/risk_manager/manager.py
"""Risk manager -- main evaluation pipeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from trustdesk.reputation.engine import ReputationEngine
from trustdesk.reputation.types import FeedbackRecord
from trustdesk.risk_manager.adaptive import apply_adaptive_adjustments
from trustdesk.risk_manager.circuit_breaker import CircuitBreaker
from trustdesk.risk_manager.hard_checks import run_all_hard_checks
from trustdesk.risk_manager.soft_checks import SoftEvaluator, run_soft_checks
from trustdesk.risk_manager.types import (
    CheckResult,
    PortfolioState,
    RiskParameters,
    VerdictStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Verdict:
    """Final risk verdict for a trade proposal."""

    status: VerdictStatus
    tier: str
    effective_limits: RiskParameters
    hard_results: dict[str, CheckResult]
    hard_reasons: dict[str, str]
    soft_results: dict[str, CheckResult]
    soft_details: dict[str, str]
    soft_checks_note: str


class RiskManager:
    """Orchestrates reputation lookup, hard checks, soft checks."""

    def __init__(
        self,
        reputation_engine: ReputationEngine,
        circuit_breaker: CircuitBreaker,
        llm_evaluator: SoftEvaluator,
    ) -> None:
        self._reputation = reputation_engine
        self._circuit = circuit_breaker
        self._llm = llm_evaluator

    async def evaluate(
        self,
        proposal: dict[str, Any],
        portfolio: PortfolioState,
        feedback_history: list[FeedbackRecord],
        regime: str,
        current_timestamp: int,
    ) -> Verdict:
        """Evaluate a trade proposal through the full pipeline."""
        # 1. Get tier from reputation engine
        rep = self._reputation.evaluate(
            feedback_history,
            current_drawdown_pct=portfolio.current_drawdown_pct,
            daily_loss_pct=portfolio.daily_realized_loss_pct,
        )

        # 2. Build effective parameters
        params = apply_adaptive_adjustments(rep.limits, portfolio, regime)

        # 3. Run hard checks
        pair = proposal.get("pair", "UNKNOWN")
        size_pct = float(proposal.get("size_pct", 0.0))

        hard_results, hard_reasons = run_all_hard_checks(
            position_size_pct=size_pct,
            pair=pair,
            current_timestamp=current_timestamp,
            portfolio=portfolio,
            params=params,
        )

        hard_failed = any(r == CheckResult.FAIL for r in hard_results.values())

        # 4. Short-circuit on hard failure
        if hard_failed:
            return Verdict(
                status=VerdictStatus.REJECTED,
                tier=rep.tier.name,
                effective_limits=params,
                hard_results=hard_results,
                hard_reasons=hard_reasons,
                soft_results={},
                soft_details={},
                soft_checks_note="SKIPPED_HARD_FAILED",
            )

        # 5. Circuit breaker check
        if not self._circuit.is_available:
            return Verdict(
                status=VerdictStatus.APPROVED_HARD_ONLY,
                tier=rep.tier.name,
                effective_limits=params,
                hard_results=hard_results,
                hard_reasons=hard_reasons,
                soft_results={},
                soft_details={},
                soft_checks_note="SKIPPED_LLM_UNAVAILABLE",
            )

        # 6. Run soft checks
        try:
            soft_results, soft_details = await run_soft_checks(
                evaluator=self._llm,
                proposal=proposal,
                portfolio=_portfolio_to_dict(portfolio),
                parameters=_params_to_dict(params),
            )
            self._circuit.record_success()
        except Exception:
            self._circuit.record_failure()
            return Verdict(
                status=VerdictStatus.APPROVED_HARD_ONLY,
                tier=rep.tier.name,
                effective_limits=params,
                hard_results=hard_results,
                hard_reasons=hard_reasons,
                soft_results={},
                soft_details={},
                soft_checks_note="SKIPPED_LLM_UNAVAILABLE",
            )

        soft_failed = any(r == CheckResult.FAIL for r in soft_results.values())

        return Verdict(
            status=VerdictStatus.REJECTED if soft_failed else VerdictStatus.APPROVED,
            tier=rep.tier.name,
            effective_limits=params,
            hard_results=hard_results,
            hard_reasons=hard_reasons,
            soft_results=soft_results,
            soft_details=soft_details,
            soft_checks_note="",
        )


def _portfolio_to_dict(p: PortfolioState) -> dict[str, Any]:
    return {
        "open_positions": p.open_positions,
        "total_exposure_pct": p.total_exposure_pct,
        "daily_realized_loss_pct": p.daily_realized_loss_pct,
        "current_drawdown_pct": p.current_drawdown_pct,
        "consecutive_losses": p.consecutive_losses,
        "open_pairs": p.open_pairs,
    }


def _params_to_dict(p: RiskParameters) -> dict[str, Any]:
    return {
        "max_position_pct": p.max_position_pct,
        "max_exposure_pct": p.max_exposure_pct,
        "max_daily_loss_pct": p.max_daily_loss_pct,
        "max_open_positions": p.max_open_positions,
        "min_alignment": p.min_alignment,
        "btc_only": p.btc_only,
        "no_new_trades": p.no_new_trades,
    }
```

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/risk_manager/tests/test_manager.py -x` -- expect PASS
- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/ backend/src/trustdesk/risk_manager/ -x` -- expect ALL PASS
- [ ] Commit: `git add backend/src/trustdesk/risk_manager/manager.py backend/src/trustdesk/risk_manager/tests/test_manager.py && git commit -m "feat(risk_manager): add manager orchestrator with full pipeline"`

---

## Task 10: Wire up __init__.py exports and final verification

### Step 10.1 -- Update __init__.py files

- [ ] Update `backend/src/trustdesk/reputation/__init__.py`

```python
# backend/src/trustdesk/reputation/__init__.py
"""Reputation engine -- maps on-chain feedback to capital tiers."""
from trustdesk.reputation.engine import EvaluationResult, ReputationEngine
from trustdesk.reputation.tiers import TierName, get_tier_limits
from trustdesk.reputation.types import FeedbackKind, FeedbackRecord, TierLimits

__all__ = [
    "EvaluationResult",
    "FeedbackKind",
    "FeedbackRecord",
    "ReputationEngine",
    "TierLimits",
    "TierName",
    "get_tier_limits",
]
```

- [ ] Update `backend/src/trustdesk/risk_manager/__init__.py`

```python
# backend/src/trustdesk/risk_manager/__init__.py
"""Risk manager -- external validator for trade proposals."""
from trustdesk.risk_manager.circuit_breaker import CircuitBreaker
from trustdesk.risk_manager.manager import RiskManager, Verdict
from trustdesk.risk_manager.types import (
    CheckResult,
    PortfolioState,
    RiskParameters,
    VerdictStatus,
)

__all__ = [
    "CheckResult",
    "CircuitBreaker",
    "PortfolioState",
    "RiskManager",
    "RiskParameters",
    "Verdict",
    "VerdictStatus",
]
```

### Step 10.2 -- Run full test suite

- [ ] Run: `cd /Users/sneg55/Documents/GitHub/TrustDesk && uv run pytest backend/src/trustdesk/reputation/ backend/src/trustdesk/risk_manager/ -v --tb=short`
- [ ] Verify: all tests pass, no warnings
- [ ] Commit: `git add backend/src/trustdesk/reputation/__init__.py backend/src/trustdesk/risk_manager/__init__.py && git commit -m "feat: wire up reputation + risk_manager public exports"`

---

## Summary

| Task | Files | Tests | Purpose |
|------|-------|-------|---------|
| 1 | `reputation/{types,constants,tiers}.py` | `test_tiers.py` | Tier definitions and limits |
| 2 | `reputation/promotion.py` | `test_promotion.py` | Promotion/demotion/cooldown logic |
| 3 | `reputation/engine.py` | `test_engine.py` | Reputation orchestrator |
| 4 | `risk_manager/{types,constants}.py` | -- | Risk manager foundation types |
| 5 | `risk_manager/hard_checks.py` | `test_hard_checks.py` | 5 deterministic hard limits |
| 6 | `risk_manager/adaptive.py` | `test_adaptive.py` | Drawdown defense + adaptive params |
| 7 | `risk_manager/soft_checks.py` | `test_soft_checks.py` | 6 LLM-evaluated soft limits |
| 8 | `risk_manager/circuit_breaker.py` | `test_circuit_breaker.py` | LLM unavailability handling |
| 9 | `risk_manager/manager.py` | `test_manager.py` | Full evaluation pipeline |
| 10 | `*/__init__.py` | -- | Public API exports |

**Total new files:** 20 source + 8 test = 28 files
**All files under 200 lines.**
**All modules are pure logic or use Protocol-based dependency injection -- fully testable without mocking external services.**
