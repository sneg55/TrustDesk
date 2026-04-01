"""Tests for KrakenClient."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from trustdesk.adapters.kraken.client import KrakenClient
from trustdesk.core.config import TrustDeskConfig


def _config(mode: str = "paper") -> TrustDeskConfig:
    return TrustDeskConfig(
        trustdesk_mode=mode,
        anthropic_api_key="test",
        trustdesk_agent_private_key="0x" + "ab" * 32,
        trustdesk_validator_private_key="0x" + "cd" * 32,
    )


def _mock_runner() -> AsyncMock:
    return AsyncMock()


TICKER_RAW: dict[str, Any] = {
    "result": {
        "XXBTZUSD": {
            "a": ["50100.00000", "1", "1.000"],
            "b": ["50000.00000", "2", "2.000"],
            "c": ["50050.00000", "0.01000000"],
            "v": ["1234.50000000", "5678.90000000"],
            "h": ["51000.00000", "52000.00000"],
            "l": ["49000.00000", "48000.00000"],
        }
    }
}

OHLC_RAW: dict[str, Any] = {
    "result": {
        "XXBTZUSD": [
            [1000, "100.0", "110.0", "90.0", "105.0", "0.0", "50.0", 10],
            [1060, "105.0", "115.0", "95.0", "110.0", "0.0", "60.0", 12],
        ]
    }
}

ORDERBOOK_RAW: dict[str, Any] = {
    "result": {
        "XXBTZUSD": {
            "asks": [["50100.00000", "1.500", 1234567890]],
            "bids": [["50000.00000", "2.000", 1234567890]],
        }
    }
}

TRADES_RAW: dict[str, Any] = {
    "result": {
        "XXBTZUSD": [
            ["50000.00000", "0.10000000", 1234567890.123, "b", "l", "", "12345"],
        ]
    }
}

BALANCE_RAW: dict[str, Any] = {
    "result": {"ZUSD": "10000.0000", "XXBT": "0.50000000"}
}

OPEN_ORDERS_RAW: dict[str, Any] = {
    "result": {
        "open": {
            "O-ABC": {
                "descr": {
                    "pair": "XBTUSD",
                    "type": "buy",
                    "ordertype": "limit",
                    "price": "50000.0",
                },
                "vol": "0.5",
                "status": "open",
            }
        }
    }
}

PLACE_ORDER_RAW: dict[str, Any] = {
    "result": {
        "descr": {"order": "buy 0.5 XBTUSD @ limit 50000.0"},
        "txid": ["O-XYZ"],
    }
}

CANCEL_ORDER_RAW: dict[str, Any] = {"result": {"count": 1}}
CANCEL_ORDER_FAIL_RAW: dict[str, Any] = {"result": {"count": 0}}

TRADE_HISTORY_RAW: dict[str, Any] = {
    "result": {
        "trades": {
            "T-123": {
                "pair": "XXBTZUSD",
                "type": "buy",
                "price": "50000.00000",
                "vol": "0.10000000",
                "cost": "5000.00000",
                "fee": "5.00000",
                "time": 1234567890.0,
            }
        }
    }
}


class TestKrakenClientTicker:
    async def test_ticker_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = TICKER_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.ticker("BTC/USD")
        assert result.pair == "BTC/USD"
        assert result.ask == 50100.0
        assert result.bid == 50000.0
        assert result.last == 50050.0
        assert result.volume_24h == 1234.5
        assert result.high_24h == 51000.0
        assert result.low_24h == 49000.0
        runner.run.assert_called_once_with("ticker", ["--pair", "XXBTZUSD"])


class TestKrakenClientOHLC:
    async def test_ohlc_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = OHLC_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.ohlc("BTC/USD", interval=1)
        assert len(result) == 2
        assert result[0].open == 100.0
        assert result[1].close == 110.0
        runner.run.assert_called_once_with("ohlc", ["--pair", "XXBTZUSD", "--interval", "1"])


class TestKrakenClientOrderbook:
    async def test_orderbook_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = ORDERBOOK_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.orderbook("BTC/USD", count=10)
        assert result.pair == "BTC/USD"
        assert result.asks[0].price == 50100.0
        assert result.bids[0].volume == 2.0
        runner.run.assert_called_once_with("depth", ["--pair", "XXBTZUSD", "--count", "10"])


class TestKrakenClientRecentTrades:
    async def test_recent_trades_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = TRADES_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.recent_trades("BTC/USD")
        assert len(result) == 1
        assert result[0].price == 50000.0
        assert result[0].side == "buy"


class TestKrakenClientBalance:
    async def test_balance_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = BALANCE_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.balance()
        assert result == {"ZUSD": 10000.0, "XXBT": 0.5}


class TestKrakenClientOpenOrders:
    async def test_open_orders_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = OPEN_ORDERS_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.open_orders()
        assert len(result) == 1
        assert result[0].order_id == "O-ABC"
        assert result[0].side == "buy"
        assert result[0].status == "open"


class TestKrakenClientPlaceOrder:
    async def test_paper_mode_uses_paper_command(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = PLACE_ORDER_RAW
        client = KrakenClient(_config("paper"), runner=runner)
        result = await client.place_order("buy", "BTC/USD", 0.5, 50000.0)
        assert result.order_id == "O-XYZ"
        runner.run.assert_called_once_with(
            "paper", ["buy", "--pair", "XXBTZUSD", "--volume", "0.5",
                      "--price", "50000.0", "--ordertype", "limit"],
        )

    async def test_live_mode_uses_order_command(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = PLACE_ORDER_RAW
        client = KrakenClient(_config("live"), runner=runner)
        result = await client.place_order("buy", "BTC/USD", 0.5, 50000.0)
        assert result.order_id == "O-XYZ"
        runner.run.assert_called_once_with(
            "order", ["buy", "--pair", "XXBTZUSD", "--volume", "0.5",
                       "--price", "50000.0", "--ordertype", "limit"],
        )


class TestKrakenClientCancelOrder:
    async def test_cancel_success(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = CANCEL_ORDER_RAW
        client = KrakenClient(_config(), runner=runner)
        assert await client.cancel_order("O-ABC") is True

    async def test_cancel_not_found(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = CANCEL_ORDER_FAIL_RAW
        client = KrakenClient(_config(), runner=runner)
        assert await client.cancel_order("O-MISSING") is False


class TestKrakenClientTradeHistory:
    async def test_trade_history_parses_response(self) -> None:
        runner = _mock_runner()
        runner.run.return_value = TRADE_HISTORY_RAW
        client = KrakenClient(_config(), runner=runner)
        result = await client.trade_history()
        assert len(result) == 1
        assert result[0].trade_id == "T-123"
        assert result[0].cost == 5000.0


class TestPairMapping:
    def test_to_kraken_pair(self) -> None:
        client = KrakenClient(_config())
        assert client._to_kraken_pair("BTC/USD") == "XXBTZUSD"
        assert client._to_kraken_pair("ETH/USD") == "XETHZUSD"
        assert client._to_kraken_pair("SOL/USD") == "SOLUSD"
