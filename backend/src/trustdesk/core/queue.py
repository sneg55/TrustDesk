"""Internal message queue for inter-process communication.

InMemoryQueue for single-process dev/testing.
PostgreSQL-backed queue for production (desk + risk_manager as separate processes).
"""
from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import AsyncIterator


class InMemoryQueue:
    """Async message queue using asyncio.Queue per channel. For dev/testing."""

    def __init__(self) -> None:
        self._channels: dict[str, list[asyncio.Queue[dict]]] = defaultdict(list)

    async def publish(self, channel: str, message: dict) -> None:
        """Publish a message to all subscribers on a channel."""
        for q in self._channels[channel]:
            await q.put(message)

    async def subscribe(self, channel: str) -> AsyncIterator[dict]:
        """Subscribe to a channel. Yields messages as they arrive."""
        q: asyncio.Queue[dict] = asyncio.Queue()
        self._channels[channel].append(q)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            self._channels[channel].remove(q)
