"""Tests for the trades endpoints."""
import pytest
from httpx import ASGITransport, AsyncClient
from trustdesk.api.app import create_app


SAMPLE_TRADES = [
    {
        "proposal_id": "p-001",
        "pair": "ETH/USDC",
        "side": "long",
        "size": 0.5,
        "status": "executed",
        "pnl": 12.50,
        "timestamp": 1711900000.0,
    },
    {
        "proposal_id": "p-002",
        "pair": "BTC/USDC",
        "side": "short",
        "size": 0.1,
        "status": "rejected",
        "pnl": 0.0,
        "timestamp": 1711900100.0,
    },
]


@pytest.fixture
def app():
    application = create_app()
    application.state.trades = SAMPLE_TRADES
    return application


@pytest.mark.asyncio
async def test_get_trades(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/trades")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_trade_by_id(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/trades/p-001")
    assert resp.status_code == 200
    assert resp.json()["proposal_id"] == "p-001"


@pytest.mark.asyncio
async def test_get_trade_not_found(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/trades/p-999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_portfolio(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert "positions" in body
    assert "nav" in body
    assert "unrealized_pnl" in body
