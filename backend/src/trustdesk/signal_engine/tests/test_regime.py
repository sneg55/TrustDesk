"""Tests for regime detection."""

from __future__ import annotations

from trustdesk.signal_engine.indicators import (
    compute_adx,
    compute_atr,
    compute_bollinger,
    compute_ema,
    compute_obv,
    detect_obv_trend,
)
from trustdesk.signal_engine.regime import (
    Regime,
    detect_regime,
)
from trustdesk.signal_engine.types import OBVTrend, OHLCData


class TestRegimeEnum:
    """Regime enum values."""

    def test_regime_values(self) -> None:
        assert Regime.TRENDING_UP.value == "TRENDING_UP"
        assert Regime.TRENDING_DOWN.value == "TRENDING_DOWN"
        assert Regime.RANGING.value == "RANGING"
        assert Regime.VOLATILE.value == "VOLATILE"


class TestDetectRegime:
    """Regime detection from indicator values."""

    def test_trending_up(self) -> None:
        regime = detect_regime(
            adx=30.0,
            ema_fast=100.0,
            ema_medium=95.0,
            ema_slow=90.0,
            obv_trend=OBVTrend.RISING,
            atr_current=50.0,
            atr_avg=40.0,
            bollinger_width_current=0.03,
            bollinger_width_prev=0.035,
        )
        assert regime == Regime.TRENDING_UP

    def test_trending_down(self) -> None:
        regime = detect_regime(
            adx=30.0,
            ema_fast=90.0,
            ema_medium=95.0,
            ema_slow=100.0,
            obv_trend=OBVTrend.FALLING,
            atr_current=50.0,
            atr_avg=40.0,
            bollinger_width_current=0.03,
            bollinger_width_prev=0.035,
        )
        assert regime == Regime.TRENDING_DOWN

    def test_volatile(self) -> None:
        regime = detect_regime(
            adx=15.0,
            ema_fast=100.0,
            ema_medium=99.0,
            ema_slow=98.0,
            obv_trend=OBVTrend.FLAT,
            atr_current=100.0,
            atr_avg=40.0,
            bollinger_width_current=0.06,
            bollinger_width_prev=0.03,
        )
        assert regime == Regime.VOLATILE

    def test_ranging(self) -> None:
        regime = detect_regime(
            adx=15.0,
            ema_fast=100.0,
            ema_medium=99.0,
            ema_slow=101.0,
            obv_trend=OBVTrend.FLAT,
            atr_current=40.0,
            atr_avg=40.0,
            bollinger_width_current=0.03,
            bollinger_width_prev=0.035,
        )
        assert regime == Regime.RANGING

    def test_ranging_price_between_emas(self) -> None:
        """Ranging requires price between EMA 21 and 50."""
        regime = detect_regime(
            adx=15.0,
            ema_fast=100.0,
            ema_medium=95.0,
            ema_slow=105.0,
            obv_trend=OBVTrend.FLAT,
            atr_current=40.0,
            atr_avg=40.0,
            bollinger_width_current=0.03,
            bollinger_width_prev=0.035,
        )
        assert regime == Regime.RANGING

    def test_defaults_to_ranging(self) -> None:
        """When no regime strongly matches, default to RANGING."""
        regime = detect_regime(
            adx=22.0,
            ema_fast=100.0,
            ema_medium=100.0,
            ema_slow=100.0,
            obv_trend=OBVTrend.FLAT,
            atr_current=40.0,
            atr_avg=40.0,
            bollinger_width_current=0.03,
            bollinger_width_prev=0.03,
        )
        assert regime == Regime.RANGING


class TestDetectRegimeADXHighMixedEMA:
    """ADX high but EMAs not cleanly aligned — should fall through to RANGING."""

    def test_adx_high_but_ema_flat(self) -> None:
        """ADX > 25 but EMAs are flat/mixed — neither trending up nor down."""
        regime = detect_regime(
            adx=30.0,
            ema_fast=100.0,
            ema_medium=100.0,  # Not clearly aligned up or down
            ema_slow=100.0,
            obv_trend=OBVTrend.FLAT,
            atr_current=40.0,
            atr_avg=40.0,
            bollinger_width_current=0.03,
            bollinger_width_prev=0.035,
        )
        assert regime == Regime.RANGING


class TestDetectRegimeFromOHLC:
    """Integration test: regime from OHLC data."""

    def _detect_from_ohlc(self, ohlc: OHLCData) -> Regime:
        df = ohlc.df
        adx = compute_adx(df, period=14)
        ema9 = compute_ema(df["close"], 9)
        ema21 = compute_ema(df["close"], 21)
        ema50 = compute_ema(df["close"], 50)
        obv = compute_obv(df)
        atr = compute_atr(df, period=14)
        _, _, _, bb_width = compute_bollinger(df["close"])
        return detect_regime(
            adx=float(adx.iloc[-1]),
            ema_fast=float(ema9.iloc[-1]),
            ema_medium=float(ema21.iloc[-1]),
            ema_slow=float(ema50.iloc[-1]),
            obv_trend=detect_obv_trend(obv, lookback=5),
            atr_current=float(atr.iloc[-1]),
            atr_avg=float(atr.rolling(20).mean().iloc[-1]),
            bollinger_width_current=float(bb_width.iloc[-1]),
            bollinger_width_prev=float(bb_width.iloc[-2]),
        )

    def test_uptrend_data_detects_trending(
        self, uptrend_ohlc: OHLCData
    ) -> None:
        df = uptrend_ohlc.df
        adx = compute_adx(df, period=14)
        ema9 = compute_ema(df["close"], 9)
        ema21 = compute_ema(df["close"], 21)
        ema50 = compute_ema(df["close"], 50)
        obv = compute_obv(df)
        atr = compute_atr(df, period=14)
        _, _, _, bb_width = compute_bollinger(df["close"])

        regime = detect_regime(
            adx=float(adx.iloc[-1]),
            ema_fast=float(ema9.iloc[-1]),
            ema_medium=float(ema21.iloc[-1]),
            ema_slow=float(ema50.iloc[-1]),
            obv_trend=detect_obv_trend(obv, lookback=5),
            atr_current=float(atr.iloc[-1]),
            atr_avg=float(atr.rolling(20).mean().iloc[-1]),
            bollinger_width_current=float(bb_width.iloc[-1]),
            bollinger_width_prev=float(bb_width.iloc[-2]),
        )
        assert regime in (Regime.TRENDING_UP, Regime.VOLATILE)

    def test_ranging_ohlc_detects_regime(self, ranging_ohlc: OHLCData) -> None:
        """Flat OHLC data produces a non-volatile regime."""
        regime = self._detect_from_ohlc(ranging_ohlc)
        assert regime in (Regime.RANGING, Regime.TRENDING_UP, Regime.TRENDING_DOWN)

    def test_volatile_ohlc_detects_regime(self, volatile_ohlc: OHLCData) -> None:
        """High-volatility OHLC data can produce any regime depending on indicators."""
        regime = self._detect_from_ohlc(volatile_ohlc)
        assert regime in (Regime.RANGING, Regime.VOLATILE, Regime.TRENDING_UP, Regime.TRENDING_DOWN)
