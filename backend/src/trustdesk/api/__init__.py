"""TrustDesk API package."""
from trustdesk.api.app import create_app
from trustdesk.api.events import Event, EventBus, EventType

__all__ = ["create_app", "EventBus", "Event", "EventType"]
