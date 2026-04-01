"""Tests for the in-process event bus."""
import asyncio
import pytest
from trustdesk.api.events import EventBus, Event, EventType


class TestEventType:
    def test_all_event_types_exist(self):
        assert EventType.PROPOSAL == "proposal"
        assert EventType.VERDICT == "verdict"
        assert EventType.EXECUTION == "execution"
        assert EventType.REPUTATION_UPDATE == "reputation_update"
        assert EventType.PASS_DECISION == "pass_decision"
        assert EventType.ON_CHAIN_CONFIRMED == "on_chain_confirmed"


class TestEvent:
    def test_event_creation(self):
        event = Event(type=EventType.PROPOSAL, data={"pair": "ETH/USDC"})
        assert event.type == EventType.PROPOSAL
        assert event.data == {"pair": "ETH/USDC"}
        assert event.timestamp is not None

    def test_event_to_dict(self):
        event = Event(type=EventType.VERDICT, data={"approved": True})
        d = event.to_dict()
        assert d["type"] == "verdict"
        assert d["data"] == {"approved": True}
        assert "timestamp" in d


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus):
        received = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(handler)
        await bus.publish(Event(type=EventType.PROPOSAL, data={"id": "t1"}))
        assert len(received) == 1
        assert received[0].data == {"id": "t1"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        count = {"a": 0, "b": 0}

        async def handler_a(event: Event):
            count["a"] += 1

        async def handler_b(event: Event):
            count["b"] += 1

        bus.subscribe(handler_a)
        bus.subscribe(handler_b)
        await bus.publish(Event(type=EventType.EXECUTION, data={}))
        assert count["a"] == 1
        assert count["b"] == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        received = []

        async def handler(event: Event):
            received.append(event)  # pragma: no cover

        bus.subscribe(handler)
        bus.unsubscribe(handler)
        await bus.publish(Event(type=EventType.VERDICT, data={}))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self, bus):
        # Should not raise
        await bus.publish(Event(type=EventType.PROPOSAL, data={}))

    @pytest.mark.asyncio
    async def test_handler_error_does_not_break_others(self, bus):
        received = []

        async def bad_handler(event: Event):
            raise ValueError("boom")

        async def good_handler(event: Event):
            received.append(event)

        bus.subscribe(bad_handler)
        bus.subscribe(good_handler)
        await bus.publish(Event(type=EventType.EXECUTION, data={}))
        assert len(received) == 1
