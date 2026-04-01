"""Tests for technical indicator calculations."""

from __future__ import annotations

import pandas as pd

from trustdesk.signal_engine.indicators import (
    compute_adx,
    compute_atr,
    compute_bollinger,
    compute_ema,
    compute_keltner,
    compute_obv,
    compute_roc,
    compute_rsi,
    compute_stochastic_rsi,
    compute_volume_sma_ratio,
    compute_vwap,
    detect_crossover,
    detect_obv_trend,
)
from trustdesk.signal_engine.types import CrossoverState, OBVTrend, OHLCData


class TestEMA:
    """EMA calculation tests."""

    def test_ema_length(self, uptrend_ohlc: OHLCData) -> None:
        result = compute_ema(uptrend_ohlc.df["close"], period=9)
        assert len(result) == len(uptrend_ohlc.df)

    def test_ema_is_series(self, uptrend_ohlc: OHLCData) -> None:
        result = compute_ema(uptrend_ohlc.df["close"], period=9)
        assert isinstance(result, pd.Series)

    def test_ema_9_above_21_in_uptrend(
        self, uptrend_ohlc: OHLCData
    ) -> None:
        ema9 = compute_ema(uptrend_ohlc.df["close"], period=9)
        ema21 = compute_ema(uptrend_ohlc.df["close"], period=21)
        assert ema9.iloc[-1] > ema21.iloc[-1]

    def test_ema_9_below_21_in_downtrend(
        self, downtrend_ohlc: OHLCData
    ) -> None:
        ema9 = compute_ema(downtrend_ohlc.df["close"], period=9)
        ema21 = compute_ema(downtrend_ohlc.df["close"], period=21)
        assert ema9.iloc[-1] < ema21.iloc[-1]


class TestCrossover:
    """EMA crossover detection."""

    def test_bullish_crossover(self, uptrend_ohlc: OHLCData) -> None:
        ema9 = compute_ema(uptrend_ohlc.df["close"], period=9)
        ema21 = compute_ema(uptrend_ohlc.df["close"], period=21)
        state = detect_crossover(ema9, ema21)
        assert state == CrossoverState.BULLISH

    def test_bearish_crossover(self, downtrend_ohlc: OHLCData) -> None:
        ema9 = compute_ema(downtrend_ohlc.df["close"], period=9)
        ema21 = compute_ema(downtrend_ohlc.df["close"], period=21)
        state = detect_crossover(ema9, ema21)
        assert state == CrossoverState.BEARISH


class TestCrossoverNeutral:
    """Edge case: exactly equal EMAs."""

    def test_neutral_when_equal(self) -> None:
        fast = pd.Series([1.0, 2.0, 3.0])
        slow = pd.Series([1.0, 2.0, 3.0])
        assert detect_crossover(fast, slow) == CrossoverState.NEUTRAL


class TestRSI:
    """RSI calculation tests."""

    def test_rsi_range(self, uptrend_ohlc: OHLCData) -> None:
        rsi = compute_rsi(uptrend_ohlc.df["close"], period=14)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_rsi_high_in_uptrend(self, uptrend_ohlc: OHLCData) -> None:
        rsi = compute_rsi(uptrend_ohlc.df["close"], period=14)
        assert rsi.iloc[-1] > 50

    def test_rsi_low_in_downtrend(
        self, downtrend_ohlc: OHLCData
    ) -> None:
        rsi = compute_rsi(downtrend_ohlc.df["close"], period=14)
        assert rsi.iloc[-1] < 50


class TestStochasticRSI:
    """Stochastic RSI tests."""

    def test_stoch_rsi_range(self, uptrend_ohlc: OHLCData) -> None:
        k, d = compute_stochastic_rsi(uptrend_ohlc.df["close"])
        valid_k = k.dropna()
        valid_d = d.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()
        assert (valid_d >= 0).all() and (valid_d <= 100).all()


class TestROC:
    """Rate of Change tests."""

    def test_roc_positive_uptrend(
        self, uptrend_ohlc: OHLCData
    ) -> None:
        roc = compute_roc(uptrend_ohlc.df["close"], period=12)
        assert roc.iloc[-1] > 0

    def test_roc_negative_downtrend(
        self, downtrend_ohlc: OHLCData
    ) -> None:
        roc = compute_roc(downtrend_ohlc.df["close"], period=12)
        assert roc.iloc[-1] < 0


class TestADX:
    """ADX calculation tests."""

    def test_adx_range(self, uptrend_ohlc: OHLCData) -> None:
        adx = compute_adx(uptrend_ohlc.df, period=14)
        valid = adx.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()


class TestATR:
    """ATR calculation tests."""

    def test_atr_positive(self, uptrend_ohlc: OHLCData) -> None:
        atr = compute_atr(uptrend_ohlc.df, period=14)
        valid = atr.dropna()
        assert (valid > 0).all()


class TestBollinger:
    """Bollinger Bands tests."""

    def test_bollinger_structure(
        self, uptrend_ohlc: OHLCData
    ) -> None:
        upper, middle, lower, width = compute_bollinger(
            uptrend_ohlc.df["close"], period=20, std_dev=2.0
        )
        assert len(upper) == len(uptrend_ohlc.df)
        valid_idx = upper.dropna().index
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()
        assert (width.dropna() >= 0).all()


class TestKeltner:
    """Keltner Channel tests."""

    def test_keltner_structure(
        self, uptrend_ohlc: OHLCData
    ) -> None:
        upper, middle, lower = compute_keltner(
            uptrend_ohlc.df, period=20, multiplier=1.5
        )
        valid_idx = upper.dropna().index
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()


class TestVolume:
    """Volume indicator tests."""

    def test_volume_sma_ratio(self, uptrend_ohlc: OHLCData) -> None:
        ratio = compute_volume_sma_ratio(
            uptrend_ohlc.df["volume"], period=20
        )
        valid = ratio.dropna()
        assert (valid > 0).all()

    def test_vwap(self, uptrend_ohlc: OHLCData) -> None:
        vwap = compute_vwap(uptrend_ohlc.df, lookback=20)
        assert len(vwap) == len(uptrend_ohlc.df)


class TestOBV:
    """On-Balance Volume tests."""

    def test_obv_length(self, uptrend_ohlc: OHLCData) -> None:
        obv = compute_obv(uptrend_ohlc.df)
        assert len(obv) == len(uptrend_ohlc.df)

    def test_obv_trend_rising_in_uptrend(
        self, uptrend_ohlc: OHLCData
    ) -> None:
        obv = compute_obv(uptrend_ohlc.df)
        trend = detect_obv_trend(obv, lookback=5)
        assert trend == OBVTrend.RISING

    def test_obv_trend_falling_in_downtrend(
        self, downtrend_ohlc: OHLCData
    ) -> None:
        obv = compute_obv(downtrend_ohlc.df)
        trend = detect_obv_trend(obv, lookback=5)
        assert trend == OBVTrend.FALLING


class TestOBVFlat:
    """Edge case: perfectly flat OBV."""

    def test_flat_obv_trend(self) -> None:
        obv = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0])
        assert detect_obv_trend(obv, lookback=5) == OBVTrend.FLAT
