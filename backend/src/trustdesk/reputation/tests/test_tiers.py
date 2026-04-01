# backend/src/trustdesk/reputation/tests/test_tiers.py
"""Tests for tier definitions and constants."""

from trustdesk.reputation.constants import (
    COOLDOWN_TRADES_REQUIRED,
    DEMOTION_CONSECUTIVE_LOSSES,
    DEMOTION_SCORE,
    PROMOTION_SCORE,
)
from trustdesk.reputation.tiers import TIER_DEFINITIONS, TierName, get_tier_limits


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
