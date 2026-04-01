"""Strategist constants: thresholds, cycle intervals, position sizing."""

# Signal alignment score thresholds
STRONG_THRESHOLD = 1.00
MODERATE_THRESHOLD = 0.80
WEAK_THRESHOLD = 0.60
NO_SIGNAL_THRESHOLD = 0.40

# Regime string values
REGIME_TRENDING_UP = "TRENDING_UP"
REGIME_TRENDING_DOWN = "TRENDING_DOWN"
REGIME_RANGING = "RANGING"
REGIME_VOLATILE = "VOLATILE"

# Cycle intervals per regime (seconds)
CYCLE_INTERVALS: dict[str, int] = {
    REGIME_TRENDING_UP: 300,    # 5 minutes
    REGIME_TRENDING_DOWN: 900,  # 15 minutes
    REGIME_RANGING: 300,        # 5 minutes
    REGIME_VOLATILE: 120,       # 2 minutes
}

# Position size multiplier per regime (1.0 = full size)
POSITION_SIZE_MULTIPLIER: dict[str, float] = {
    REGIME_TRENDING_UP: 1.0,
    REGIME_TRENDING_DOWN: 0.0,   # default PASS
    REGIME_RANGING: 1.0,
    REGIME_VOLATILE: 0.5,
}

# Default cycle interval fallback
DEFAULT_CYCLE_INTERVAL = 300
