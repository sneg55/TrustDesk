"""WebSocket endpoint for real-time event streaming."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from trustdesk.api.events import Event, EventBus

logger = logging.getLogger(__name__)


def attach_websocket(app: FastAPI, bus: EventBus) -> None:
    """Attach the /ws WebSocket endpoint to the app."""

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        queue: asyncio.Queue[Event] = asyncio.Queue()

        async def forward_to_queue(event: Event) -> None:
            await queue.put(event)

        bus.subscribe(forward_to_queue)
        try:
            while True:
                event = await queue.get()
                await ws.send_json(event.to_dict())
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")  # pragma: no cover
        except Exception:  # pragma: no cover
            logger.exception("WebSocket error")
        finally:
            bus.unsubscribe(forward_to_queue)
