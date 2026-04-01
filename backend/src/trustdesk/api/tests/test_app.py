"""Integration tests for the full FastAPI app."""
import pytest
from httpx import ASGITransport, AsyncClient
from trustdesk.api.app import create_app
from trustdesk.api.events import EventBus


@pytest.fixture
def app():
    bus = EventBus()
    return create_app(event_bus=bus)


@pytest.mark.asyncio
async def test_app_has_cors_headers(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


@pytest.mark.asyncio
async def test_all_routes_registered(app):
    routes = [r.path for r in app.routes]
    assert "/health" in routes
    assert "/api/trades" in routes
    assert "/api/trades/{proposal_id}" in routes
    assert "/api/reputation" in routes
    assert "/api/portfolio" in routes
    assert "/ws" in routes


@pytest.mark.asyncio
async def test_event_bus_on_app_state(app):
    assert hasattr(app.state, "event_bus")
    assert isinstance(app.state.event_bus, EventBus)
