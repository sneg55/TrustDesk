"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trustdesk.api.events import EventBus
from trustdesk.api.routes.health import router as health_router
from trustdesk.api.routes.reputation import router as reputation_router
from trustdesk.api.routes.trades import router as trades_router


def create_app(event_bus: EventBus | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if event_bus is None:
        event_bus = EventBus()

    app = FastAPI(title="TrustDesk API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.event_bus = event_bus

    app.include_router(health_router)
    app.include_router(trades_router, prefix="/api")
    app.include_router(reputation_router, prefix="/api")

    from trustdesk.api.websocket import attach_websocket

    attach_websocket(app, event_bus)

    return app
