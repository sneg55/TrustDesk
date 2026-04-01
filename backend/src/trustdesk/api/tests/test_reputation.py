"""Tests for the reputation endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient

from trustdesk.api.app import create_app

SAMPLE_REPUTATION = {
    "tier": "EXPLORER",
    "score": 42,
    "total_trades": 15,
    "successful_trades": 10,
    "promotion_history": [
        {"from": "NOVICE", "to": "EXPLORER", "timestamp": 1711800000.0}
    ],
}


@pytest.fixture
def app():
    application = create_app()
    application.state.reputation = SAMPLE_REPUTATION
    return application


@pytest.mark.asyncio
async def test_get_reputation(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/reputation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "EXPLORER"
    assert body["score"] == 42


@pytest.mark.asyncio
async def test_reputation_includes_promotion_history(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/reputation")
    body = resp.json()
    assert len(body["promotion_history"]) == 1
    assert body["promotion_history"][0]["to"] == "EXPLORER"


@pytest.mark.asyncio
async def test_reputation_default_when_no_data():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/reputation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "NOVICE"
    assert body["score"] == 0
