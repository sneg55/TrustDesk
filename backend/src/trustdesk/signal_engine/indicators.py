"""Technical indicator calculations using pandas.

All functions are pure: DataFrame/Series in, result out. No side effects.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trustdesk.signal_engine.types import CrossoverState, OBVTrend


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def detect_crossover(
    fast: pd.Series, slow: pd.Series
) -> CrossoverState:
    """Detect crossover state from last values of two EMAs."""
    if fast.iloc[-1] > slow.iloc[-1]:
        return CrossoverState.BULLISH
    if fast.iloc[-1] < slow.iloc[-1]:
        return CrossoverState.BEARISH
    return CrossoverState.NEUTRAL


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_stochastic_rsi(
    series: pd.Series,
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic RSI returning %K and %D lines."""
    rsi = compute_rsi(series, rsi_period)
    lowest = rsi.rolling(stoch_period).min()
    highest = rsi.rolling(stoch_period).max()
    denom = highest - lowest
    stoch = ((rsi - lowest) / denom.replace(0, np.nan)) * 100
    k = stoch.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def compute_roc(series: pd.Series, period: int = 12) -> pd.Series:
    """Rate of Change (percentage)."""
    shifted = series.shift(period)
    return ((series - shifted) / shifted) * 100


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = low.diff().mul(-1)
    plus_dm = plus_dm.where(
        (plus_dm > minus_dm) & (plus_dm > 0), 0.0
    )
    minus_dm = minus_dm.where(
        (minus_dm > plus_dm) & (minus_dm > 0), 0.0
    )
    tr = _true_range(high, low, close)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    plus_di = 100 * (
        plus_dm.ewm(alpha=1 / period, min_periods=period).mean()
        / atr
    )
    minus_di = 100 * (
        minus_dm.ewm(alpha=1 / period, min_periods=period).mean()
        / atr
    )
    dx = (
        (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0, np.nan)
        * 100
    )
    adx = dx.ewm(alpha=1 / period, min_periods=period).mean()
    return adx


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr = _true_range(df["high"], df["low"], df["close"])
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def _true_range(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> pd.Series:
    """True Range helper."""
    prev_close = close.shift(1)
    r1 = high - low
    r2 = (high - prev_close).abs()
    r3 = (low - prev_close).abs()
    return pd.concat([r1, r2, r3], axis=1).max(axis=1)


def compute_bollinger(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: upper, middle, lower, width."""
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    width = (upper - lower) / middle
    return upper, middle, lower, width


def compute_keltner(
    df: pd.DataFrame,
    period: int = 20,
    multiplier: float = 1.5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Keltner Channel: upper, middle, lower."""
    middle = compute_ema(df["close"], period)
    atr = compute_atr(df, period)
    upper = middle + multiplier * atr
    lower = middle - multiplier * atr
    return upper, middle, lower


def compute_volume_sma_ratio(
    volume: pd.Series, period: int = 20
) -> pd.Series:
    """Volume relative to its SMA."""
    sma = volume.rolling(period).mean()
    return volume / sma


def compute_vwap(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Rolling VWAP over a lookback window."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    vol_price = typical * df["volume"]
    cum_vp = vol_price.rolling(lookback).sum()
    cum_vol = df["volume"].rolling(lookback).sum()
    return cum_vp / cum_vol


def compute_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(df["close"].diff())
    direction.iloc[0] = 0
    return (direction * df["volume"]).cumsum()


def detect_obv_trend(
    obv: pd.Series, lookback: int = 5
) -> OBVTrend:
    """Determine OBV trend from recent slope."""
    recent = obv.iloc[-lookback:]
    slope = np.polyfit(range(len(recent)), recent.values, 1)[0]
    # Use a relative tolerance to handle floating-point near-zero slopes
    threshold = max(abs(recent.values).mean() * 1e-10, 1e-10)
    if slope > threshold:
        return OBVTrend.RISING
    if slope < -threshold:
        return OBVTrend.FALLING
    return OBVTrend.FLAT
