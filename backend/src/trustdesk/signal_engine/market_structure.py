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
