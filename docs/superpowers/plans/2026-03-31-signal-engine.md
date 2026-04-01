# Signal Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the deterministic Signal Engine that ingests market data and outputs SignalPayload objects with regime detection, indicator calculations, and alignment scoring.

**Architecture:** Pure computation layer. No LLM. Takes market data from Kraken adapter, computes indicators with pandas, detects regime, scores signal alignment, outputs SignalPayload.

**Tech Stack:** pandas, asyncio (engine.py only)

---

## Task 1: Define internal types and constants

### Step 1.1: Write tests for types

**File:** `backend/src/trustdesk/signal_engine/tests/test_types.py`

```python
"""Tests for signal engine internal types."""

from __future__ import annotations

import pandas as pd
import pytest

from trustdesk.signal_engine.types import (
    CrossoverState,
    OBVTrend,
    OHLCData,
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


class TestOHLCData:
    """OHLCData validation and construction."""

    def test_valid_ohlc(self) -> None:
        data = OHLCData(
            pair="BTCUSD",
            interval=15,
            df=pd.DataFrame(
                {
                    "timestamp": [1.0, 2.0],
                    "open": [100.0, 101.0],
                    "high": [102.0, 103.0],
                    "low": [99.0, 100.0],
                    "close": [101.0, 102.0],
                    "volume": [10.0, 11.0],
                    "vwap": [100.5, 101.5],
                    "count": [5, 6],
                }
            ),
        )
        assert data.pair == "BTCUSD"
        assert data.interval == 15
        assert len(data.df) == 2

    def test_missing_column_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing required columns"):
            OHLCData(
                pair="BTCUSD",
                interval=15,
                df=pd.DataFrame({"open": [1.0], "close": [2.0]}),
            )


class TestTickerData:
    """TickerData construction."""

    def test_valid_ticker(self) -> None:
        t = TickerData(
            pair="BTCUSD",
            ask=100.5,
            bid=100.0,
            last=100.2,
            volume_today=1500.0,
            vwap_today=100.1,
        )
        assert t.spread == pytest.approx(0.5)
        assert t.spread_pct == pytest.approx(0.5 / 100.2 * 100)


class TestOrderBookSnapshot:
    """OrderBookSnapshot construction."""

    def test_valid_book(self) -> None:
        book = OrderBookSnapshot(
            pair="BTCUSD",
            asks=pd.DataFrame(
                {"price": [101.0, 102.0], "volume": [1.0, 2.0]}
            ),
            bids=pd.DataFrame(
                {"price": [100.0, 99.0], "volume": [1.5, 2.5]}
            ),
        )
        assert len(book.asks) == 2
        assert len(book.bids) == 2


class TestTradeFlowData:
    """TradeFlowData construction."""

    def test_valid_trade_flow(self) -> None:
        tf = TradeFlowData(
            pair="BTCUSD",
            df=pd.DataFrame(
                {
                    "price": [100.0, 101.0],
                    "volume": [1.0, 2.0],
                    "time": [1.0, 2.0],
                    "side": ["buy", "sell"],
                }
            ),
        )
        assert len(tf.df) == 2

    def test_missing_column_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing required columns"):
            TradeFlowData(
                pair="BTCUSD",
                df=pd.DataFrame({"price": [100.0]}),
            )


class TestEnums:
    """Enum types."""

    def test_crossover_state_values(self) -> None:
        assert CrossoverState.BULLISH.value == "BULLISH"
        assert CrossoverState.BEARISH.value == "BEARISH"
        assert CrossoverState.NEUTRAL.value == "NEUTRAL"

    def test_obv_trend_values(self) -> None:
        assert OBVTrend.RISING.value == "RISING"
        assert OBVTrend.FALLING.value == "FALLING"
        assert OBVTrend.FLAT.value == "FLAT"
```

### Step 1.2: Implement types

**File:** `backend/src/trustdesk/signal_engine/types.py`

```python
"""Internal types for the signal engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass

import pandas as pd

OHLC_REQUIRED_COLS = frozenset(
    {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "count",
    }
)

TRADE_REQUIRED_COLS = frozenset({"price", "volume", "time", "side"})


class CrossoverState(enum.Enum):
    """EMA crossover direction."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class OBVTrend(enum.Enum):
    """On-Balance Volume trend direction."""

    RISING = "RISING"
    FALLING = "FALLING"
    FLAT = "FLAT"


@dataclass(frozen=True)
class OHLCData:
    """Validated OHLC candlestick data."""

    pair: str
    interval: int
    df: pd.DataFrame

    def __post_init__(self) -> None:
        missing = OHLC_REQUIRED_COLS - set(self.df.columns)
        if missing:
            msg = f"Missing required columns: {sorted(missing)}"
            raise ValueError(msg)


@dataclass(frozen=True)
class TickerData:
    """Current ticker snapshot."""

    pair: str
    ask: float
    bid: float
    last: float
    volume_today: float
    vwap_today: float

    @property
    def spread(self) -> float:
        """Absolute spread."""
        return self.ask - self.bid

    @property
    def spread_pct(self) -> float:
        """Spread as percentage of last price."""
        return (self.spread / self.last) * 100


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Order book snapshot with asks and bids."""

    pair: str
    asks: pd.DataFrame
    bids: pd.DataFrame


@dataclass(frozen=True)
class TradeFlowData:
    """Recent trade data for flow analysis."""

    pair: str
    df: pd.DataFrame

    def __post_init__(self) -> None:
        missing = TRADE_REQUIRED_COLS - set(self.df.columns)
        if missing:
            msg = f"Missing required columns: {sorted(missing)}"
            raise ValueError(msg)
```

### Step 1.3: Write tests for constants

**File:** `backend/src/trustdesk/signal_engine/tests/test_constants.py`

```python
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
```

### Step 1.4: Implement constants

**File:** `backend/src/trustdesk/signal_engine/constants.py`

```python
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
```

### Step 1.5: Update `__init__.py` exports

**File:** `backend/src/trustdesk/signal_engine/__init__.py`

```python
"""Signal Engine: deterministic market signal computation."""

from __future__ import annotations
```

### Step 1.6: Verify

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/test_types.py src/trustdesk/signal_engine/tests/test_constants.py -v
```

### Step 1.7: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/signal_engine/types.py \
       backend/src/trustdesk/signal_engine/constants.py \
       backend/src/trustdesk/signal_engine/__init__.py \
       backend/src/trustdesk/signal_engine/tests/test_types.py \
       backend/src/trustdesk/signal_engine/tests/test_constants.py
git commit -m "feat(signal-engine): add internal types and constants"
```

---

## Task 2: Implement trend and momentum indicators

### Step 2.1: Write test fixtures (conftest)

**File:** `backend/src/trustdesk/signal_engine/tests/conftest.py`

```python
"""Shared fixtures for signal engine tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trustdesk.signal_engine.types import (
    OHLCData,
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


def _make_ohlc_df(
    n: int = 60,
    base_price: float = 50000.0,
    trend: float = 0.001,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic OHLC data with optional trend."""
    rng = np.random.default_rng(seed)
    timestamps = np.arange(n, dtype=float)
    closes = np.empty(n)
    closes[0] = base_price
    for i in range(1, n):
        ret = trend + rng.normal(0, 0.005)
        closes[i] = closes[i - 1] * (1 + ret)

    opens = closes * (1 + rng.normal(0, 0.001, n))
    highs = np.maximum(opens, closes) * (1 + rng.uniform(0, 0.005, n))
    lows = np.minimum(opens, closes) * (1 - rng.uniform(0, 0.005, n))
    volumes = rng.uniform(100, 500, n)
    vwaps = (highs + lows + closes) / 3
    counts = rng.integers(50, 200, n)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "vwap": vwaps,
            "count": counts,
        }
    )


@pytest.fixture()
def uptrend_ohlc() -> OHLCData:
    """60 candles with an uptrend (0.2% per bar)."""
    return OHLCData(
        pair="BTCUSD",
        interval=15,
        df=_make_ohlc_df(n=60, trend=0.002, seed=42),
    )


@pytest.fixture()
def downtrend_ohlc() -> OHLCData:
    """60 candles with a downtrend (-0.2% per bar)."""
    return OHLCData(
        pair="BTCUSD",
        interval=15,
        df=_make_ohlc_df(n=60, trend=-0.002, seed=42),
    )


@pytest.fixture()
def ranging_ohlc() -> OHLCData:
    """60 candles with no trend (flat)."""
    return OHLCData(
        pair="BTCUSD",
        interval=15,
        df=_make_ohlc_df(n=60, trend=0.0, seed=42),
    )


@pytest.fixture()
def volatile_ohlc() -> OHLCData:
    """60 candles with high volatility."""
    df = _make_ohlc_df(n=60, trend=0.0, seed=42)
    df["high"] = df["high"] * 1.02
    df["low"] = df["low"] * 0.98
    return OHLCData(pair="BTCUSD", interval=15, df=df)


@pytest.fixture()
def sample_ticker() -> TickerData:
    """A sample ticker snapshot."""
    return TickerData(
        pair="BTCUSD",
        ask=50100.0,
        bid=50000.0,
        last=50050.0,
        volume_today=1500.0,
        vwap_today=50025.0,
    )


@pytest.fixture()
def bullish_orderbook() -> OrderBookSnapshot:
    """Order book with stronger bids (bullish imbalance)."""
    return OrderBookSnapshot(
        pair="BTCUSD",
        asks=pd.DataFrame(
            {
                "price": [50100.0 + i * 10 for i in range(25)],
                "volume": [0.5] * 25,
            }
        ),
        bids=pd.DataFrame(
            {
                "price": [50000.0 - i * 10 for i in range(25)],
                "volume": [1.5] * 25,
            }
        ),
    )


@pytest.fixture()
def balanced_orderbook() -> OrderBookSnapshot:
    """Order book with balanced bids and asks."""
    return OrderBookSnapshot(
        pair="BTCUSD",
        asks=pd.DataFrame(
            {
                "price": [50100.0 + i * 10 for i in range(25)],
                "volume": [1.0] * 25,
            }
        ),
        bids=pd.DataFrame(
            {
                "price": [50000.0 - i * 10 for i in range(25)],
                "volume": [1.0] * 25,
            }
        ),
    )


@pytest.fixture()
def buy_heavy_trades() -> TradeFlowData:
    """Recent trades dominated by buy-side."""
    return TradeFlowData(
        pair="BTCUSD",
        df=pd.DataFrame(
            {
                "price": [50050.0 + i for i in range(20)],
                "volume": [1.0] * 20,
                "time": [float(i) for i in range(20)],
                "side": ["buy"] * 15 + ["sell"] * 5,
            }
        ),
    )
```

### Step 2.2: Write tests for indicators (trend + momentum)

**File:** `backend/src/trustdesk/signal_engine/tests/test_indicators.py`

```python
"""Tests for technical indicator calculations."""

from __future__ import annotations

import pandas as pd
import pytest

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
```

### Step 2.3: Implement indicators

**File:** `backend/src/trustdesk/signal_engine/indicators.py`

```python
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
    if slope > 0:
        return OBVTrend.RISING
    if slope < 0:
        return OBVTrend.FALLING
    return OBVTrend.FLAT
```

### Step 2.4: Verify

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/test_indicators.py -v
```

### Step 2.5: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/signal_engine/indicators.py \
       backend/src/trustdesk/signal_engine/tests/test_indicators.py \
       backend/src/trustdesk/signal_engine/tests/conftest.py
git commit -m "feat(signal-engine): implement technical indicators"
```

---

## Task 3: Implement market structure analysis

### Step 3.1: Write tests for market structure

**File:** `backend/src/trustdesk/signal_engine/tests/test_market_structure.py`

```python
"""Tests for market structure analysis."""

from __future__ import annotations

import pytest

from trustdesk.signal_engine.market_structure import (
    compute_book_imbalance,
    compute_spread_pct,
    compute_trade_flow_direction,
)
from trustdesk.signal_engine.types import (
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


class TestBookImbalance:
    """Order book imbalance ratio tests."""

    def test_bullish_imbalance(
        self, bullish_orderbook: OrderBookSnapshot
    ) -> None:
        ratio = compute_book_imbalance(bullish_orderbook)
        assert ratio > 0.55

    def test_balanced_book(
        self, balanced_orderbook: OrderBookSnapshot
    ) -> None:
        ratio = compute_book_imbalance(balanced_orderbook)
        assert ratio == pytest.approx(0.5)

    def test_ratio_bounded(
        self, bullish_orderbook: OrderBookSnapshot
    ) -> None:
        ratio = compute_book_imbalance(bullish_orderbook)
        assert 0.0 <= ratio <= 1.0


class TestTradeFlow:
    """Trade flow direction tests."""

    def test_buy_heavy_positive(
        self, buy_heavy_trades: TradeFlowData
    ) -> None:
        direction = compute_trade_flow_direction(buy_heavy_trades)
        assert direction > 0.0

    def test_direction_bounded(
        self, buy_heavy_trades: TradeFlowData
    ) -> None:
        direction = compute_trade_flow_direction(buy_heavy_trades)
        assert -1.0 <= direction <= 1.0


class TestSpread:
    """Spread percentage tests."""

    def test_spread_pct(self, sample_ticker: TickerData) -> None:
        spread = compute_spread_pct(sample_ticker)
        expected = (100.0 / 50050.0) * 100
        assert spread == pytest.approx(expected)

    def test_spread_positive(self, sample_ticker: TickerData) -> None:
        spread = compute_spread_pct(sample_ticker)
        assert spread > 0.0
```

### Step 3.2: Implement market structure

**File:** `backend/src/trustdesk/signal_engine/market_structure.py`

```python
"""Market structure analysis: order book, trade flow, spread.

Pure functions. No side effects.
"""

from __future__ import annotations

from trustdesk.signal_engine.types import (
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


def compute_book_imbalance(book: OrderBookSnapshot) -> float:
    """Compute bid/ask volume imbalance ratio.

    Returns value in [0, 1]. Values > 0.5 indicate stronger bids
    (bullish), values < 0.5 indicate stronger asks (bearish).
    """
    bid_vol = float(book.bids["volume"].sum())
    ask_vol = float(book.asks["volume"].sum())
    total = bid_vol + ask_vol
    if total == 0:
        return 0.5
    return bid_vol / total


def compute_trade_flow_direction(trades: TradeFlowData) -> float:
    """Compute net trade flow direction.

    Returns value in [-1, 1]. Positive means buy-dominated,
    negative means sell-dominated.
    """
    df = trades.df
    buy_mask = df["side"] == "buy"
    buy_vol = float(df.loc[buy_mask, "volume"].sum())
    sell_vol = float(df.loc[~buy_mask, "volume"].sum())
    total = buy_vol + sell_vol
    if total == 0:
        return 0.0
    return (buy_vol - sell_vol) / total


def compute_spread_pct(ticker: TickerData) -> float:
    """Spread as percentage of last price."""
    return ticker.spread_pct
```

### Step 3.3: Verify

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/test_market_structure.py -v
```

### Step 3.4: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/signal_engine/market_structure.py \
       backend/src/trustdesk/signal_engine/tests/test_market_structure.py
git commit -m "feat(signal-engine): implement market structure analysis"
```

---

## Task 4: Implement regime detection

### Step 4.1: Write tests for regime detection

**File:** `backend/src/trustdesk/signal_engine/tests/test_regime.py`

```python
"""Tests for regime detection."""

from __future__ import annotations

import numpy as np
import pandas as pd

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


class TestDetectRegimeFromOHLC:
    """Integration test: regime from OHLC data."""

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
```

### Step 4.2: Implement regime detection

**File:** `backend/src/trustdesk/signal_engine/regime.py`

```python
"""Regime detection for market state classification.

Pure function. Takes pre-computed indicator values and returns
a Regime classification.
"""

from __future__ import annotations

import enum

from trustdesk.signal_engine.constants import (
    ADX_RANGING_THRESHOLD,
    ADX_TRENDING_THRESHOLD,
    ATR_VOLATILE_MULTIPLIER,
)
from trustdesk.signal_engine.types import OBVTrend


class Regime(enum.Enum):
    """Market regime classification."""

    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"


def detect_regime(
    *,
    adx: float,
    ema_fast: float,
    ema_medium: float,
    ema_slow: float,
    obv_trend: OBVTrend,
    atr_current: float,
    atr_avg: float,
    bollinger_width_current: float,
    bollinger_width_prev: float,
) -> Regime:
    """Detect market regime from indicator values.

    Priority order: VOLATILE > TRENDING > RANGING (default).
    """
    # -- Volatile: ATR spike + Bollinger expanding rapidly --
    bb_expanding = bollinger_width_current > bollinger_width_prev * 1.5
    if atr_current > ATR_VOLATILE_MULTIPLIER * atr_avg and bb_expanding:
        return Regime.VOLATILE

    # -- Trending: ADX > 25, EMA alignment, OBV confirmation --
    if adx > ADX_TRENDING_THRESHOLD:
        if (
            ema_fast > ema_medium > ema_slow
            and obv_trend == OBVTrend.RISING
        ):
            return Regime.TRENDING_UP
        if (
            ema_fast < ema_medium < ema_slow
            and obv_trend == OBVTrend.FALLING
        ):
            return Regime.TRENDING_DOWN

    # -- Ranging: ADX < 20, Bollinger contracting, price between EMAs --
    bb_contracting = bollinger_width_current <= bollinger_width_prev
    ema_min = min(ema_medium, ema_slow)
    ema_max = max(ema_medium, ema_slow)
    price_between = ema_min <= ema_fast <= ema_max

    if adx < ADX_RANGING_THRESHOLD and (
        bb_contracting or price_between
    ):
        return Regime.RANGING

    # Default: RANGING
    return Regime.RANGING
```

### Step 4.3: Verify

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/test_regime.py -v
```

### Step 4.4: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/signal_engine/regime.py \
       backend/src/trustdesk/signal_engine/tests/test_regime.py
git commit -m "feat(signal-engine): implement regime detection"
```

---

## Task 5: Implement alignment scoring

### Step 5.1: Write tests for alignment scoring

**File:** `backend/src/trustdesk/signal_engine/tests/test_alignment.py`

```python
"""Tests for signal alignment scoring."""

from __future__ import annotations

import pytest

from trustdesk.schemas.signal_payload import Alignment
from trustdesk.signal_engine.alignment import (
    compute_alignment,
    compute_derived_values,
    compute_position_size,
    compute_stop_distance,
)
from trustdesk.signal_engine.regime import Regime
from trustdesk.signal_engine.types import CrossoverState, OBVTrend


class TestComputeAlignment:
    """Alignment score computation."""

    def test_strong_alignment(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.RISING,
            book_imbalance=0.65,
        )
        assert result.score == pytest.approx(1.0)
        assert result.grade == Alignment.STRONG

    def test_moderate_alignment(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.RISING,
            book_imbalance=0.45,
        )
        assert result.score == pytest.approx(0.8)
        assert result.grade == Alignment.MODERATE

    def test_weak_alignment(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=0.8,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.score == pytest.approx(0.4)
        assert result.grade == Alignment.NO_SIGNAL

    def test_no_signal(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BEARISH,
            adx=22.0,
            volume_multiplier=0.8,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.score <= 0.4
        assert result.grade == Alignment.NO_SIGNAL

    def test_three_of_five(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.score == pytest.approx(0.6)
        assert result.grade == Alignment.WEAK


class TestAlignmentBreakdown:
    """Individual signal contributions."""

    def test_breakdown_keys(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BULLISH,
            adx=30.0,
            volume_multiplier=1.5,
            obv_trend=OBVTrend.RISING,
            book_imbalance=0.65,
        )
        assert result.breakdown.ema_crossover is True
        assert result.breakdown.adx_trending is True
        assert result.breakdown.volume_confirmed is True
        assert result.breakdown.obv_aligned is True
        assert result.breakdown.book_imbalance_aligned is True

    def test_all_false_breakdown(self) -> None:
        result = compute_alignment(
            crossover=CrossoverState.BEARISH,
            adx=22.0,
            volume_multiplier=0.8,
            obv_trend=OBVTrend.FALLING,
            book_imbalance=0.45,
        )
        assert result.breakdown.ema_crossover is False
        assert result.breakdown.volume_confirmed is False
        assert result.breakdown.obv_aligned is False
        assert result.breakdown.book_imbalance_aligned is False


class TestStopDistance:
    """Stop distance from ATR."""

    def test_stop_distance(self) -> None:
        assert compute_stop_distance(100.0) == pytest.approx(150.0)

    def test_stop_distance_small(self) -> None:
        assert compute_stop_distance(10.0) == pytest.approx(15.0)


class TestPositionSize:
    """Position sizing from alignment grade."""

    def test_strong(self) -> None:
        assert compute_position_size(Alignment.STRONG) == 10.0

    def test_moderate(self) -> None:
        assert compute_position_size(Alignment.MODERATE) == 8.0

    def test_weak(self) -> None:
        assert compute_position_size(Alignment.WEAK) == 5.0

    def test_no_signal(self) -> None:
        assert compute_position_size(Alignment.NO_SIGNAL) == 0.0


class TestDerivedValues:
    """Derived values computation."""

    def test_derived_strong_aligned(self) -> None:
        dv = compute_derived_values(
            atr=100.0,
            grade=Alignment.STRONG,
            regime=Regime.TRENDING_UP,
        )
        assert dv.suggested_stop_distance == pytest.approx(150.0)
        assert dv.position_size_pct == 10.0
        assert dv.regime_aligned is True

    def test_derived_ranging_not_aligned(self) -> None:
        dv = compute_derived_values(
            atr=100.0,
            grade=Alignment.STRONG,
            regime=Regime.RANGING,
        )
        assert dv.regime_aligned is False

    def test_derived_no_signal_zero_size(self) -> None:
        dv = compute_derived_values(
            atr=100.0,
            grade=Alignment.NO_SIGNAL,
            regime=Regime.TRENDING_UP,
        )
        assert dv.position_size_pct == 0.0
```

### Step 5.2: Implement alignment scoring

**File:** `backend/src/trustdesk/signal_engine/alignment.py`

```python
"""Signal alignment scoring and derived value computation.

Pure functions that compute alignment from indicator outputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from trustdesk.schemas.signal_payload import (
    Alignment,
    AlignmentBreakdown,
    DerivedValues,
)
from trustdesk.signal_engine.constants import (
    ADX_RANGING_THRESHOLD,
    ADX_TRENDING_THRESHOLD,
    BOOK_IMBALANCE_THRESHOLD,
    POSITION_SIZE_MODERATE,
    POSITION_SIZE_NONE,
    POSITION_SIZE_STRONG,
    POSITION_SIZE_WEAK,
    STOP_ATR_MULTIPLIER,
    VOLUME_THRESHOLD,
)
from trustdesk.signal_engine.regime import Regime
from trustdesk.signal_engine.types import CrossoverState, OBVTrend

_TOTAL_SIGNALS = 5


@dataclass(frozen=True)
class AlignmentResult:
    """Result of alignment computation."""

    score: float
    grade: Alignment
    breakdown: AlignmentBreakdown


def compute_alignment(
    *,
    crossover: CrossoverState,
    adx: float,
    volume_multiplier: float,
    obv_trend: OBVTrend,
    book_imbalance: float,
) -> AlignmentResult:
    """Compute alignment score from directional signals.

    Counts how many of 5 key signals agree on a long bias.
    """
    ema_ok = crossover == CrossoverState.BULLISH
    adx_ok = adx > ADX_TRENDING_THRESHOLD or adx < ADX_RANGING_THRESHOLD
    vol_ok = volume_multiplier > VOLUME_THRESHOLD
    obv_ok = obv_trend == OBVTrend.RISING
    book_ok = book_imbalance > BOOK_IMBALANCE_THRESHOLD

    count = sum([ema_ok, adx_ok, vol_ok, obv_ok, book_ok])
    score = count / _TOTAL_SIGNALS

    if score >= 1.0:
        grade = Alignment.STRONG
    elif score >= 0.8:
        grade = Alignment.MODERATE
    elif score >= 0.6:
        grade = Alignment.WEAK
    else:
        grade = Alignment.NO_SIGNAL

    breakdown = AlignmentBreakdown(
        ema_crossover=ema_ok,
        adx_trending=adx_ok,
        volume_confirmed=vol_ok,
        obv_aligned=obv_ok,
        book_imbalance_aligned=book_ok,
    )
    return AlignmentResult(
        score=score, grade=grade, breakdown=breakdown
    )


def compute_stop_distance(atr: float) -> float:
    """Suggested stop distance = 1.5 * ATR."""
    return STOP_ATR_MULTIPLIER * atr


def compute_position_size(grade: Alignment) -> float:
    """Position size percentage from alignment grade."""
    return {
        Alignment.STRONG: POSITION_SIZE_STRONG,
        Alignment.MODERATE: POSITION_SIZE_MODERATE,
        Alignment.WEAK: POSITION_SIZE_WEAK,
        Alignment.NO_SIGNAL: POSITION_SIZE_NONE,
    }[grade]


def compute_derived_values(
    *,
    atr: float,
    grade: Alignment,
    regime: Regime,
) -> DerivedValues:
    """Compute derived trading values."""
    regime_aligned = regime in (
        Regime.TRENDING_UP,
        Regime.TRENDING_DOWN,
    )
    return DerivedValues(
        suggested_stop_distance=compute_stop_distance(atr),
        position_size_pct=compute_position_size(grade),
        regime_aligned=regime_aligned,
    )
```

### Step 5.3: Verify

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/test_alignment.py -v
```

### Step 5.4: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/signal_engine/alignment.py \
       backend/src/trustdesk/signal_engine/tests/test_alignment.py
git commit -m "feat(signal-engine): implement alignment scoring and derived values"
```

---

## Task 6: Implement the main engine

### Step 6.1: Define the Kraken adapter protocol

Add the protocol to `types.py` (append to existing file):

**Append to:** `backend/src/trustdesk/signal_engine/types.py`

```python
# Add these imports at the top:
from typing import Protocol

# Add this class at the bottom of the file:

class MarketDataProvider(Protocol):
    """Protocol for market data sources (e.g., Kraken adapter).

    The signal engine depends on this interface, not on a concrete
    Kraken implementation. Any object with these async methods works.
    """

    async def ticker(self, pair: str) -> TickerData: ...

    async def ohlc(
        self, pair: str, interval: int
    ) -> OHLCData: ...

    async def orderbook(
        self, pair: str, count: int
    ) -> OrderBookSnapshot: ...

    async def recent_trades(
        self, pair: str
    ) -> TradeFlowData: ...
```

### Step 6.2: Write tests for the engine

**File:** `backend/src/trustdesk/signal_engine/tests/test_engine.py`

```python
"""Tests for the main signal engine cycle."""

from __future__ import annotations

from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest

from trustdesk.schemas.signal_payload import Alignment, SignalPayload
from trustdesk.signal_engine.engine import SignalEngine
from trustdesk.signal_engine.tests.conftest import _make_ohlc_df
from trustdesk.signal_engine.types import (
    OHLCData,
    OrderBookSnapshot,
    TickerData,
    TradeFlowData,
)


def _mock_provider(
    pair: str = "BTCUSD",
    trend: float = 0.002,
    seed: int = 42,
) -> AsyncMock:
    """Create a mock MarketDataProvider."""
    provider = AsyncMock()

    ohlc_df = _make_ohlc_df(n=60, trend=trend, seed=seed)
    provider.ticker.return_value = TickerData(
        pair=pair,
        ask=float(ohlc_df["close"].iloc[-1]) + 50,
        bid=float(ohlc_df["close"].iloc[-1]) - 50,
        last=float(ohlc_df["close"].iloc[-1]),
        volume_today=1500.0,
        vwap_today=float(ohlc_df["vwap"].iloc[-1]),
    )

    async def mock_ohlc(p: str, interval: int) -> OHLCData:
        return OHLCData(pair=p, interval=interval, df=ohlc_df.copy())

    provider.ohlc.side_effect = mock_ohlc

    provider.orderbook.return_value = OrderBookSnapshot(
        pair=pair,
        asks=pd.DataFrame(
            {
                "price": [
                    float(ohlc_df["close"].iloc[-1]) + 10 * i
                    for i in range(1, 26)
                ],
                "volume": [0.5] * 25,
            }
        ),
        bids=pd.DataFrame(
            {
                "price": [
                    float(ohlc_df["close"].iloc[-1]) - 10 * i
                    for i in range(1, 26)
                ],
                "volume": [1.5] * 25,
            }
        ),
    )

    provider.recent_trades.return_value = TradeFlowData(
        pair=pair,
        df=pd.DataFrame(
            {
                "price": [
                    float(ohlc_df["close"].iloc[-1]) + i
                    for i in range(20)
                ],
                "volume": [1.0] * 20,
                "time": [float(i) for i in range(20)],
                "side": ["buy"] * 15 + ["sell"] * 5,
            }
        ),
    )
    return provider


class TestSignalEngine:
    """Main engine cycle tests."""

    @pytest.mark.asyncio()
    async def test_run_cycle_returns_payload(self) -> None:
        provider = _mock_provider(trend=0.002)
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert isinstance(payload, SignalPayload)

    @pytest.mark.asyncio()
    async def test_payload_has_pair(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.pair == "BTCUSD"

    @pytest.mark.asyncio()
    async def test_payload_has_regime(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.regime in (
            "TRENDING_UP",
            "TRENDING_DOWN",
            "RANGING",
            "VOLATILE",
        )

    @pytest.mark.asyncio()
    async def test_payload_has_alignment(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.alignment in (
            Alignment.STRONG,
            Alignment.MODERATE,
            Alignment.WEAK,
            Alignment.NO_SIGNAL,
        )

    @pytest.mark.asyncio()
    async def test_payload_has_derived_values(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert payload.derived.suggested_stop_distance > 0
        assert payload.derived.position_size_pct >= 0
        assert isinstance(payload.derived.regime_aligned, bool)

    @pytest.mark.asyncio()
    async def test_payload_has_score(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert 0.0 <= payload.alignment_score <= 1.0

    @pytest.mark.asyncio()
    async def test_downtrend_provider(self) -> None:
        provider = _mock_provider(trend=-0.002)
        engine = SignalEngine(provider=provider)
        payload = await engine.run_cycle("BTCUSD")
        assert isinstance(payload, SignalPayload)

    @pytest.mark.asyncio()
    async def test_provider_called_correctly(self) -> None:
        provider = _mock_provider()
        engine = SignalEngine(provider=provider)
        await engine.run_cycle("BTCUSD")
        provider.ticker.assert_called_once_with("BTCUSD")
        assert provider.ohlc.call_count == 3  # 15m, 1H, 4H
        provider.orderbook.assert_called_once_with("BTCUSD", count=25)
        provider.recent_trades.assert_called_once_with("BTCUSD")
```

### Step 6.3: Implement the engine

**File:** `backend/src/trustdesk/signal_engine/engine.py`

```python
"""Main signal engine: ingest -> compute -> output.

This is the only async module. It calls the MarketDataProvider
and orchestrates pure computation functions.
"""

from __future__ import annotations

from trustdesk.schemas.signal_payload import SignalPayload
from trustdesk.signal_engine.alignment import (
    compute_alignment,
    compute_derived_values,
)
from trustdesk.signal_engine.constants import (
    ADX_PERIOD,
    ATR_PERIOD,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    EMA_FAST,
    EMA_MEDIUM,
    EMA_SLOW,
    OBV_LOOKBACK,
    TIMEFRAMES,
    VOLUME_SMA_PERIOD,
)
from trustdesk.signal_engine.indicators import (
    compute_adx,
    compute_atr,
    compute_bollinger,
    compute_ema,
    compute_obv,
    compute_rsi,
    compute_volume_sma_ratio,
    detect_crossover,
    detect_obv_trend,
)
from trustdesk.signal_engine.market_structure import (
    compute_book_imbalance,
    compute_spread_pct,
    compute_trade_flow_direction,
)
from trustdesk.signal_engine.regime import detect_regime
from trustdesk.signal_engine.types import MarketDataProvider


class SignalEngine:
    """Orchestrates one signal computation cycle."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    async def run_cycle(self, pair: str) -> SignalPayload:
        """Run one full signal computation cycle."""
        # -- Fetch data --
        ticker = await self._provider.ticker(pair)
        ohlc_map = {
            tf: await self._provider.ohlc(pair, tf)
            for tf in TIMEFRAMES
        }
        book = await self._provider.orderbook(pair, count=25)
        trades = await self._provider.recent_trades(pair)

        # Use 15m for primary indicators
        df_15 = ohlc_map[15].df

        return self._compute(pair, ticker, df_15, book, trades)

    def _compute(
        self, pair, ticker, df, book, trades
    ) -> SignalPayload:
        """Pure computation from fetched data."""
        # -- Trend indicators --
        ema9 = compute_ema(df["close"], EMA_FAST)
        ema21 = compute_ema(df["close"], EMA_MEDIUM)
        ema50 = compute_ema(df["close"], EMA_SLOW)
        crossover = detect_crossover(ema9, ema21)
        adx = compute_adx(df, ADX_PERIOD)

        # -- Momentum --
        rsi = compute_rsi(df["close"])

        # -- Volatility --
        atr = compute_atr(df, ATR_PERIOD)
        _, _, _, bb_width = compute_bollinger(
            df["close"], BOLLINGER_PERIOD, BOLLINGER_STD
        )

        # -- Volume --
        vol_ratio = compute_volume_sma_ratio(
            df["volume"], VOLUME_SMA_PERIOD
        )
        obv = compute_obv(df)
        obv_trend = detect_obv_trend(obv, OBV_LOOKBACK)

        # -- Market structure --
        book_imbalance = compute_book_imbalance(book)
        trade_flow = compute_trade_flow_direction(trades)
        spread_pct = compute_spread_pct(ticker)

        # -- Regime --
        atr_val = float(atr.iloc[-1])
        atr_avg = float(atr.rolling(20).mean().iloc[-1])
        regime = detect_regime(
            adx=float(adx.iloc[-1]),
            ema_fast=float(ema9.iloc[-1]),
            ema_medium=float(ema21.iloc[-1]),
            ema_slow=float(ema50.iloc[-1]),
            obv_trend=obv_trend,
            atr_current=atr_val,
            atr_avg=atr_avg,
            bollinger_width_current=float(bb_width.iloc[-1]),
            bollinger_width_prev=float(bb_width.iloc[-2]),
        )

        # -- Alignment --
        alignment_result = compute_alignment(
            crossover=crossover,
            adx=float(adx.iloc[-1]),
            volume_multiplier=float(vol_ratio.iloc[-1]),
            obv_trend=obv_trend,
            book_imbalance=book_imbalance,
        )

        # -- Derived values --
        derived = compute_derived_values(
            atr=atr_val,
            grade=alignment_result.grade,
            regime=regime,
        )

        return SignalPayload(
            pair=pair,
            price=ticker.last,
            regime=regime.value,
            alignment=alignment_result.grade,
            alignment_score=alignment_result.score,
            breakdown=alignment_result.breakdown,
            derived=derived,
            indicators={
                "ema_9": float(ema9.iloc[-1]),
                "ema_21": float(ema21.iloc[-1]),
                "ema_50": float(ema50.iloc[-1]),
                "rsi_14": float(rsi.iloc[-1]),
                "adx_14": float(adx.iloc[-1]),
                "atr_14": atr_val,
                "bollinger_width": float(bb_width.iloc[-1]),
                "volume_multiplier": float(vol_ratio.iloc[-1]),
                "book_imbalance": book_imbalance,
                "trade_flow": trade_flow,
                "spread_pct": spread_pct,
            },
        )
```

### Step 6.4: Update `__init__.py` with public API

**File:** `backend/src/trustdesk/signal_engine/__init__.py`

```python
"""Signal Engine: deterministic market signal computation."""

from __future__ import annotations

from trustdesk.signal_engine.engine import SignalEngine
from trustdesk.signal_engine.regime import Regime
from trustdesk.signal_engine.types import MarketDataProvider

__all__ = ["MarketDataProvider", "Regime", "SignalEngine"]
```

### Step 6.5: Verify all tests pass

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/ -v
```

### Step 6.6: Verify coverage

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/ --cov=trustdesk.signal_engine --cov-report=term-missing
```

### Step 6.7: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/signal_engine/engine.py \
       backend/src/trustdesk/signal_engine/types.py \
       backend/src/trustdesk/signal_engine/__init__.py \
       backend/src/trustdesk/signal_engine/tests/test_engine.py
git commit -m "feat(signal-engine): implement main engine cycle with async data fetching"
```

---

## Task 7: Coverage gap-filling and final polish

### Step 7.1: Check coverage gaps

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/ --cov=trustdesk.signal_engine --cov-report=term-missing --cov-fail-under=100
```

### Step 7.2: Add edge case tests if needed

Likely coverage gaps and their fixes:

**Neutral crossover** (indicators.py line for `CrossoverState.NEUTRAL`):

Add to `test_indicators.py`:

```python
class TestCrossoverNeutral:
    """Edge case: exactly equal EMAs."""

    def test_neutral_when_equal(self) -> None:
        fast = pd.Series([1.0, 2.0, 3.0])
        slow = pd.Series([1.0, 2.0, 3.0])
        assert detect_crossover(fast, slow) == CrossoverState.NEUTRAL
```

**OBV trend FLAT** (indicators.py `OBVTrend.FLAT` branch):

Add to `test_indicators.py`:

```python
class TestOBVFlat:
    """Edge case: perfectly flat OBV."""

    def test_flat_obv_trend(self) -> None:
        obv = pd.Series([100.0, 100.0, 100.0, 100.0, 100.0])
        assert detect_obv_trend(obv, lookback=5) == OBVTrend.FLAT
```

**Zero total volume in order book** (market_structure.py):

Add to `test_market_structure.py`:

```python
class TestEdgeCases:
    """Edge cases for market structure functions."""

    def test_zero_volume_book(self) -> None:
        book = OrderBookSnapshot(
            pair="BTCUSD",
            asks=pd.DataFrame({"price": [100.0], "volume": [0.0]}),
            bids=pd.DataFrame({"price": [99.0], "volume": [0.0]}),
        )
        assert compute_book_imbalance(book) == 0.5

    def test_zero_volume_trades(self) -> None:
        trades = TradeFlowData(
            pair="BTCUSD",
            df=pd.DataFrame(
                {
                    "price": [100.0],
                    "volume": [0.0],
                    "time": [1.0],
                    "side": ["buy"],
                }
            ),
        )
        assert compute_trade_flow_direction(trades) == 0.0
```

### Step 7.3: Verify 100% coverage

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/signal_engine/tests/ --cov=trustdesk.signal_engine --cov-report=term-missing --cov-fail-under=100
```

### Step 7.4: Run full project test suite

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest --cov --cov-fail-under=100
```

### Step 7.5: Commit

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add -A backend/src/trustdesk/signal_engine/
git commit -m "test(signal-engine): achieve 100% coverage with edge case tests"
```

---

## Summary of Files

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `types.py` | ~90 | OHLCData, TickerData, OrderBookSnapshot, TradeFlowData, MarketDataProvider |
| `constants.py` | ~40 | All thresholds, periods, sizing constants |
| `indicators.py` | ~160 | EMA, RSI, StochRSI, ROC, ADX, ATR, Bollinger, Keltner, OBV, VWAP, volume |
| `market_structure.py` | ~45 | Book imbalance, trade flow direction, spread |
| `regime.py` | ~55 | Regime enum + detect_regime() |
| `alignment.py` | ~85 | Alignment scoring, position sizing, derived values |
| `engine.py` | ~120 | Async orchestration: fetch -> compute -> SignalPayload |
| `__init__.py` | ~8 | Public API exports |
| `tests/conftest.py` | ~130 | Fixtures: uptrend/downtrend/ranging OHLC, ticker, orderbook, trades |
| `tests/test_types.py` | ~90 | Type validation tests |
| `tests/test_constants.py` | ~75 | Constants value tests |
| `tests/test_indicators.py` | ~160 | All indicator tests |
| `tests/test_market_structure.py` | ~75 | Market structure tests |
| `tests/test_regime.py` | ~110 | Regime detection tests |
| `tests/test_alignment.py` | ~120 | Alignment and derived value tests |
| `tests/test_engine.py` | ~110 | End-to-end engine cycle tests |

## Dependencies to Add

Ensure `pyproject.toml` includes:

```toml
[project]
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]
```

## Architecture Notes

- **No ta-lib**: All indicators use pure pandas/numpy. Same interfaces, no C dependency.
- **Protocol-based DI**: `MarketDataProvider` is a `Protocol` -- the engine never imports the Kraken adapter. Tests use `AsyncMock`.
- **Pure computation core**: Only `engine.py` is async. All other modules are pure functions: DataFrame in, result out.
- **Deterministic**: No randomness, no LLM calls, no external state. Same input always produces same output.
