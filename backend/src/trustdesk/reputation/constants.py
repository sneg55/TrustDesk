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
