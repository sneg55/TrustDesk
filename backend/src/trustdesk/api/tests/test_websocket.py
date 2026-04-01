"""Tests for the WebSocket endpoint and event forwarding."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from trustdesk.api.app import create_app
from trustdesk.api.events import EventBus, Event, EventType
from trustdesk.api.websocket import attach_websocket


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def app(bus):
    application = create_app(event_bus=bus)
    attach_websocket(application, bus)
    return application


class TestWebSocket:
    def test_connect_and_receive_event(self, app, bus):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            # Publish an event from another "thread"
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                bus.publish(Event(type=EventType.PROPOSAL, data={"pair": "ETH/USDC"}))
            )
            loop.close()
            msg = ws.receive_json()
            assert msg["type"] == "proposal"
            assert msg["data"]["pair"] == "ETH/USDC"

    def test_multiple_events(self, app, bus):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                bus.publish(Event(type=EventType.VERDICT, data={"approved": True}))
            )
            loop.run_until_complete(
                bus.publish(Event(type=EventType.EXECUTION, data={"filled": True}))
            )
            loop.close()
            msg1 = ws.receive_json()
            msg2 = ws.receive_json()
            assert msg1["type"] == "verdict"
            assert msg2["type"] == "execution"

    def test_disconnect_cleans_up(self, app, bus):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            pass  # Disconnect
        # Bus should have no lingering handlers after disconnect
        assert len(bus._handlers) == 0
