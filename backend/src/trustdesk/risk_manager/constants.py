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
