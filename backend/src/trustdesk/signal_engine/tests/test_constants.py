"""Tests for signal engine constants."""

from __future__ import annotations

from trustdesk.signal_engine.constants import (
    ADX_PERIOD,
    ADX_RANGING_THRESHOLD,
    ADX_TRENDING_THRESHOLD,
    ALIGNMENT_MODERATE_THRESHOLD,
    ALIGNMENT_STRONG_THRESHOLD,
    ALIGNMENT_WEAK_THRESHOLD,
    ATR_PERIOD,
    ATR_VOLATILE_MULTIPLIER,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    BOOK_IMBALANCE_THRESHOLD,
    EMA_FAST,
    EMA_MEDIUM,
    EMA_SLOW,
    KELTNER_MULTIPLIER,
    KELTNER_PERIOD,
    OBV_LOOKBACK,
    PAIRS,
    POSITION_SIZE_MODERATE,
    POSITION_SIZE_NONE,
    POSITION_SIZE_STRONG,
    POSITION_SIZE_WEAK,
    ROC_PERIOD,
    RSI_PERIOD,
    STOP_ATR_MULTIPLIER,
    TIMEFRAMES,
    VOLUME_SMA_PERIOD,
    VOLUME_THRESHOLD,
    VWAP_LOOKBACK,
)


class TestIndicatorConstants:
    """Indicator parameter constants."""

    def test_ema_periods(self) -> None:
        assert EMA_FAST == 9
        assert EMA_MEDIUM == 21
        assert EMA_SLOW == 50

    def test_rsi_period(self) -> None:
        assert RSI_PERIOD == 14

    def test_adx_period(self) -> None:
        assert ADX_PERIOD == 14
        assert ADX_TRENDING_THRESHOLD == 25
        assert ADX_RANGING_THRESHOLD == 20

    def test_atr_period(self) -> None:
        assert ATR_PERIOD == 14
        assert ATR_VOLATILE_MULTIPLIER == 2.0

    def test_bollinger_params(self) -> None:
        assert BOLLINGER_PERIOD == 20
        assert BOLLINGER_STD == 2.0

    def test_keltner_params(self) -> None:
        assert KELTNER_PERIOD == 20
        assert KELTNER_MULTIPLIER == 1.5

    def test_volume_params(self) -> None:
        assert VOLUME_SMA_PERIOD == 20
        assert VOLUME_THRESHOLD == 1.2
        assert OBV_LOOKBACK == 5
        assert VWAP_LOOKBACK == 20

    def test_roc_period(self) -> None:
        assert ROC_PERIOD == 12


class TestAlignmentConstants:
    """Alignment scoring constants."""

    def test_thresholds(self) -> None:
        assert ALIGNMENT_STRONG_THRESHOLD == 1.0
        assert ALIGNMENT_MODERATE_THRESHOLD == 0.8
        assert ALIGNMENT_WEAK_THRESHOLD == 0.6

    def test_book_imbalance(self) -> None:
        assert BOOK_IMBALANCE_THRESHOLD == 0.55

    def test_volume_threshold(self) -> None:
        assert VOLUME_THRESHOLD == 1.2


class TestPositionSizing:
    """Position sizing constants."""

    def test_position_sizes(self) -> None:
        assert POSITION_SIZE_STRONG == 10.0
        assert POSITION_SIZE_MODERATE == 8.0
        assert POSITION_SIZE_WEAK == 5.0
        assert POSITION_SIZE_NONE == 0.0

    def test_stop_multiplier(self) -> None:
        assert STOP_ATR_MULTIPLIER == 1.5


class TestPairsAndTimeframes:
    """Trading pairs and timeframes."""

    def test_pairs(self) -> None:
        assert PAIRS == ("BTCUSD", "ETHUSD", "SOLUSD")

    def test_timeframes(self) -> None:
        assert TIMEFRAMES == (15, 60, 240)
