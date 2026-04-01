"""Signal engine constants and thresholds."""

from __future__ import annotations

# -- Trading pairs and timeframes --
PAIRS: tuple[str, ...] = ("BTCUSD", "ETHUSD", "SOLUSD")
TIMEFRAMES: tuple[int, ...] = (15, 60, 240)  # 15m, 1H, 4H

# -- EMA periods --
EMA_FAST: int = 9
EMA_MEDIUM: int = 21
EMA_SLOW: int = 50

# -- RSI --
RSI_PERIOD: int = 14

# -- ADX --
ADX_PERIOD: int = 14
ADX_TRENDING_THRESHOLD: int = 25
ADX_RANGING_THRESHOLD: int = 20

# -- ATR --
ATR_PERIOD: int = 14
ATR_VOLATILE_MULTIPLIER: float = 2.0

# -- Bollinger Bands --
BOLLINGER_PERIOD: int = 20
BOLLINGER_STD: float = 2.0

# -- Keltner Channel --
KELTNER_PERIOD: int = 20
KELTNER_MULTIPLIER: float = 1.5

# -- Volume --
VOLUME_SMA_PERIOD: int = 20
VOLUME_THRESHOLD: float = 1.2
OBV_LOOKBACK: int = 5
VWAP_LOOKBACK: int = 20

# -- Rate of Change --
ROC_PERIOD: int = 12

# -- Alignment scoring --
ALIGNMENT_STRONG_THRESHOLD: float = 1.0
ALIGNMENT_MODERATE_THRESHOLD: float = 0.8
ALIGNMENT_WEAK_THRESHOLD: float = 0.6
BOOK_IMBALANCE_THRESHOLD: float = 0.55

# -- Position sizing (percentage of portfolio) --
POSITION_SIZE_STRONG: float = 10.0
POSITION_SIZE_MODERATE: float = 8.0
POSITION_SIZE_WEAK: float = 5.0
POSITION_SIZE_NONE: float = 0.0

# -- Stop loss --
STOP_ATR_MULTIPLIER: float = 1.5
