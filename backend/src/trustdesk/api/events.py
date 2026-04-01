"""In-process async event bus for real-time streaming."""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    """All event types pushed to the dashboard."""

    PROPOSAL = "proposal"
    VERDICT = "verdict"
    EXECUTION = "execution"
    REPUTATION_UPDATE = "reputation_update"
    PASS_DECISION = "pass_decision"
    ON_CHAIN_CONFIRMED = "on_chain_confirmed"


@dataclass
class Event:
    """A single event published on the bus."""

    type: EventType
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, Enum) else self.type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Simple in-process async pub/sub."""

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        self._handlers = [h for h in self._handlers if h is not handler]

    async def publish(self, event: Event) -> None:
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for event %s",
                    handler.__name__,
                    event.type,
                )
