"""Main signal engine: ingest -> compute -> output.

This is the only async module. It calls the MarketDataProvider
and orchestrates pure computation functions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from trustdesk.schemas.signal_payload import SignalPayload

logger = logging.getLogger(__name__)
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

if TYPE_CHECKING:
    from trustdesk.signal_engine.types import MarketDataProvider


class SignalEngine:
    """Orchestrates one signal computation cycle."""

    def __init__(self, provider: MarketDataProvider, strykr=None) -> None:
        self._provider = provider
        self.strykr = strykr

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

        payload = self._compute(pair, ticker, df_15, book, trades)

        if self.strykr:
            base_symbol = pair.split("/")[0]
            try:
                signals_data = await self.strykr.signals(base_symbol)
                payload.indicators["prism_overall_signal"] = signals_data.get("overall_signal", "neutral")
                payload.indicators["prism_direction"] = signals_data.get("direction", "neutral")
                payload.indicators["prism_strength"] = signals_data.get("strength", "weak")
                payload.indicators["prism_net_score"] = signals_data.get("net_score", 0)
            except Exception as e:
                logger.warning("Strykr signals fetch failed for %s: %s", base_symbol, e)

            try:
                risk_data = await self.strykr.risk(base_symbol)
                payload.indicators["prism_daily_volatility"] = risk_data.get("daily_volatility", 0.0)
                payload.indicators["prism_current_drawdown"] = risk_data.get("current_drawdown", 0.0)
                payload.indicators["prism_sharpe_ratio"] = risk_data.get("sharpe_ratio", 0.0)
            except Exception as e:
                logger.warning("Strykr risk fetch failed for %s: %s", base_symbol, e)

        return payload

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
