"""Unified Kraken CLI client. MCP primary, subprocess fallback."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from trustdesk.adapters.kraken.types import (
    Candle,
    Order,
    OrderBook,
    OrderBookEntry,
    OrderResult,
    TickerData,
    Trade,
    TradeRecord,
)
from trustdesk.core.logging import get_logger

if TYPE_CHECKING:
    from trustdesk.core.config import TrustDeskConfig

log = get_logger(__name__)

PAIR_MAP: dict[str, str] = {
    "BTC/USD": "XXBTZUSD",
    "ETH/USD": "XETHZUSD",
    "SOL/USD": "SOLUSD",
}

SIDE_MAP: dict[str, str] = {"b": "buy", "s": "sell"}


class Runner(Protocol):
    """Protocol for CLI runners (subprocess or MCP)."""

    async def run(self, command: str, args: list[str]) -> dict[str, Any]: ...


class KrakenClient:
    """Unified interface for Kraken CLI."""

    def __init__(self, config: TrustDeskConfig, runner: Runner | None = None) -> None:
        self._config = config
        if runner is not None:
            self._runner = runner
        else:
            from trustdesk.adapters.kraken.subprocess_runner import SubprocessRunner

            self._runner = SubprocessRunner()

    def _to_kraken_pair(self, pair: str) -> str:
        """Convert standard pair (BTC/USD) to Kraken pair (XXBTZUSD)."""
        return PAIR_MAP.get(pair, pair.replace("/", ""))

    async def ticker(self, pair: str) -> TickerData:
        """Get current ticker data for a pair."""
        kpair = self._to_kraken_pair(pair)
        raw = await self._runner.run("ticker", ["--pair", kpair])
        data = next(iter(raw["result"].values()))
        return TickerData(
            pair=pair,
            ask=float(data["a"][0]),
            bid=float(data["b"][0]),
            last=float(data["c"][0]),
            volume_24h=float(data["v"][0]),
            high_24h=float(data["h"][0]),
            low_24h=float(data["l"][0]),
        )

    async def ohlc(self, pair: str, interval: int) -> list[Candle]:
        """Get OHLC candles for a pair."""
        kpair = self._to_kraken_pair(pair)
        raw = await self._runner.run("ohlc", ["--pair", kpair, "--interval", str(interval)])
        rows = next(iter(raw["result"].values()))
        return [
            Candle(
                timestamp=int(r[0]),
                open=float(r[1]),
                high=float(r[2]),
                low=float(r[3]),
                close=float(r[4]),
                volume=float(r[6]),
            )
            for r in rows
        ]

    async def orderbook(self, pair: str, count: int) -> OrderBook:
        """Get order book snapshot."""
        kpair = self._to_kraken_pair(pair)
        raw = await self._runner.run("depth", ["--pair", kpair, "--count", str(count)])
        data = next(iter(raw["result"].values()))
        return OrderBook(
            pair=pair,
            asks=[OrderBookEntry(price=float(a[0]), volume=float(a[1])) for a in data["asks"]],
            bids=[OrderBookEntry(price=float(b[0]), volume=float(b[1])) for b in data["bids"]],
        )

    async def recent_trades(self, pair: str) -> list[Trade]:
        """Get recent trades."""
        kpair = self._to_kraken_pair(pair)
        raw = await self._runner.run("trades", ["--pair", kpair])
        rows = next(iter(raw["result"].values()))
        return [
            Trade(
                price=float(r[0]),
                volume=float(r[1]),
                time=float(r[2]),
                side=SIDE_MAP.get(r[3], r[3]),
            )
            for r in rows
        ]

    async def balance(self) -> dict[str, float]:
        """Get account balances."""
        raw = await self._runner.run("balance", [])
        return {k: float(v) for k, v in raw["result"].items()}

    async def open_orders(self) -> list[Order]:
        """Get all open orders."""
        raw = await self._runner.run("open-orders", [])
        orders = raw["result"].get("open", {})
        return [
            Order(
                order_id=oid,
                pair=info["descr"]["pair"],
                side=info["descr"]["type"],
                order_type=info["descr"]["ordertype"],
                price=float(info["descr"]["price"]),
                volume=float(info["vol"]),
                status=info["status"],
            )
            for oid, info in orders.items()
        ]

    async def place_order(
        self,
        side: str,
        pair: str,
        volume: float,
        price: float,
        order_type: str = "limit",
    ) -> OrderResult:
        """Place a buy/sell order. Uses paper mode or live mode."""
        kpair = self._to_kraken_pair(pair)
        command = "paper" if self._config.mode == "paper" else "order"
        args = [
            side,
            "--pair", kpair,
            "--volume", str(volume),
            "--price", str(price),
            "--ordertype", order_type,
        ]
        raw = await self._runner.run(command, args)
        txid = raw["result"]["txid"][0]
        desc = raw["result"]["descr"]["order"]
        return OrderResult(order_id=txid, status="pending", description=desc)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID. Returns True if cancelled."""
        raw = await self._runner.run("cancel", ["--txid", order_id])
        return int(raw["result"]["count"]) > 0

    async def trade_history(self) -> list[TradeRecord]:
        """Get trade history."""
        raw = await self._runner.run("trades-history", [])
        trades = raw["result"].get("trades", {})
        return [
            TradeRecord(
                trade_id=tid,
                pair=info["pair"],
                side=info["type"],
                price=float(info["price"]),
                volume=float(info["vol"]),
                cost=float(info["cost"]),
                fee=float(info["fee"]),
                time=float(info["time"]),
            )
            for tid, info in trades.items()
        ]
