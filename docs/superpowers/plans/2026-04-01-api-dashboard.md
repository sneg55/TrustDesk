# API + Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the FastAPI backend (REST + WebSocket) and React dashboard (Activity Feed, PnL, Reputation panels) for real-time monitoring.

**Architecture:** FastAPI app with event bus for real-time WebSocket streaming. React SPA with Tailwind styling consuming the WebSocket feed.

**Tech Stack:** FastAPI, WebSocket, Recharts, viem, Tailwind CSS

---

## Task 1: Event Bus (`backend/src/trustdesk/api/events.py`)

### 1a. Write tests — `backend/src/trustdesk/api/tests/test_events.py`

```python
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
            received.append(event)

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
```

### 1b. Implement — `backend/src/trustdesk/api/events.py`

```python
"""In-process async event bus for real-time streaming."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class EventType(str, Enum):
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
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/test_events.py -v`

---

## Task 2: Health Route (`backend/src/trustdesk/api/routes/health.py`)

### 2a. Write tests — `backend/src/trustdesk/api/tests/test_health.py`

```python
"""Tests for the health endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient
from trustdesk.api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_returns_ok(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_health_includes_version(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
    body = resp.json()
    assert "version" in body
```

### 2b. Implement — `backend/src/trustdesk/api/routes/health.py`

```python
"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
```

### 2c. App factory (stub needed for health test) — `backend/src/trustdesk/api/app.py`

```python
"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trustdesk.api.events import EventBus
from trustdesk.api.routes.health import router as health_router
from trustdesk.api.routes.trades import router as trades_router
from trustdesk.api.routes.reputation import router as reputation_router


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

    return app
```

### 2d. Route `__init__.py` — `backend/src/trustdesk/api/routes/__init__.py`

```python
"""API route modules."""
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/test_health.py -v`

---

## Task 3: Trades Routes (`backend/src/trustdesk/api/routes/trades.py`)

### 3a. Write tests — `backend/src/trustdesk/api/tests/test_trades.py`

```python
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
```

### 3b. Implement — `backend/src/trustdesk/api/routes/trades.py`

```python
"""Trade history and portfolio endpoints."""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _get_trades(request: Request) -> list[dict]:
    """Get trades from app state (DB in production)."""
    return getattr(request.app.state, "trades", [])


@router.get("/trades")
async def list_trades(request: Request) -> list[dict]:
    """Return all trade history."""
    return _get_trades(request)


@router.get("/trades/{proposal_id}")
async def get_trade(proposal_id: str, request: Request) -> dict:
    """Return a single trade by proposal ID."""
    trades = _get_trades(request)
    for trade in trades:
        if trade["proposal_id"] == proposal_id:
            return trade
    raise HTTPException(status_code=404, detail=f"Trade {proposal_id} not found")


@router.get("/portfolio")
async def get_portfolio(request: Request) -> dict:
    """Return current portfolio summary."""
    trades = _get_trades(request)
    executed = [t for t in trades if t.get("status") == "executed"]
    total_pnl = sum(t.get("pnl", 0.0) for t in executed)
    return {
        "positions": executed,
        "nav": 10000.0 + total_pnl,
        "unrealized_pnl": total_pnl,
    }
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/test_trades.py -v`

---

## Task 4: Reputation Route (`backend/src/trustdesk/api/routes/reputation.py`)

### 4a. Write tests — `backend/src/trustdesk/api/tests/test_reputation.py`

```python
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
```

### 4b. Implement — `backend/src/trustdesk/api/routes/reputation.py`

```python
"""Reputation and tier endpoints."""
from fastapi import APIRouter, Request

router = APIRouter()

DEFAULT_REPUTATION = {
    "tier": "NOVICE",
    "score": 0,
    "total_trades": 0,
    "successful_trades": 0,
    "promotion_history": [],
}


@router.get("/reputation")
async def get_reputation(request: Request) -> dict:
    """Return current reputation summary."""
    return getattr(request.app.state, "reputation", DEFAULT_REPUTATION)
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/test_reputation.py -v`

---

## Task 5: WebSocket Endpoint (`backend/src/trustdesk/api/websocket.py`)

### 5a. Write tests — `backend/src/trustdesk/api/tests/test_websocket.py`

```python
"""Tests for the WebSocket endpoint and event forwarding."""
import asyncio
import json
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
```

### 5b. Implement — `backend/src/trustdesk/api/websocket.py`

```python
"""WebSocket endpoint for real-time event streaming."""
from __future__ import annotations

import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

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
            logger.info("WebSocket client disconnected")
        except Exception:
            logger.exception("WebSocket error")
        finally:
            bus.unsubscribe(forward_to_queue)
```

### 5c. Wire WebSocket into app factory

Update `backend/src/trustdesk/api/app.py` — add at the end of `create_app`:

```python
    from trustdesk.api.websocket import attach_websocket
    attach_websocket(app, event_bus)

    return app
```

The full updated `create_app` function:

```python
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
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/test_websocket.py -v`

---

## Task 6: App Integration Tests (`backend/src/trustdesk/api/tests/test_app.py`)

```python
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
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/ -v`

---

## Task 7: API `__init__.py` files

### `backend/src/trustdesk/api/__init__.py`

```python
"""TrustDesk API package."""
from trustdesk.api.app import create_app
from trustdesk.api.events import EventBus, Event, EventType

__all__ = ["create_app", "EventBus", "Event", "EventType"]
```

### `backend/src/trustdesk/api/tests/__init__.py`

```python
"""API test package."""
```

**Verify:** `cd backend && python -m pytest src/trustdesk/api/tests/ -v --tb=short`

---

## Task 8: Dashboard Types (`dashboard/src/types/index.ts`)

```typescript
/** Event types matching the backend EventType enum. */
export type EventType =
  | "proposal"
  | "verdict"
  | "execution"
  | "reputation_update"
  | "pass_decision"
  | "on_chain_confirmed";

/** A single event from the WebSocket stream. */
export interface TrustDeskEvent {
  type: EventType;
  data: Record<string, unknown>;
  timestamp: number;
}

/** Trade record from GET /api/trades. */
export interface Trade {
  proposal_id: string;
  pair: string;
  side: "long" | "short";
  size: number;
  status: "executed" | "rejected" | "modified" | "skipped";
  pnl: number;
  timestamp: number;
}

/** Portfolio from GET /api/portfolio. */
export interface Portfolio {
  positions: Trade[];
  nav: number;
  unrealized_pnl: number;
}

/** Reputation from GET /api/reputation. */
export interface Reputation {
  tier: string;
  score: number;
  total_trades: number;
  successful_trades: number;
  promotion_history: PromotionRecord[];
}

export interface PromotionRecord {
  from: string;
  to: string;
  timestamp: number;
}
```

---

## Task 9: WebSocket Hook (`dashboard/src/hooks/useWebSocket.ts`)

```typescript
import { useEffect, useRef, useState, useCallback } from "react";
import type { TrustDeskEvent } from "../types";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws";
const MAX_EVENTS = 200;
const RECONNECT_MS = 3000;

export function useWebSocket() {
  const [events, setEvents] = useState<TrustDeskEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (msg) => {
      const event: TrustDeskEvent = JSON.parse(msg.data);
      setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, RECONNECT_MS);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, connected };
}
```

---

## Task 10: WebSocket Service (`dashboard/src/services/websocket.ts`)

```typescript
/**
 * Low-level WebSocket helpers.
 * The useWebSocket hook uses this internally.
 */
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function fetchTrades() {
  const resp = await fetch(`${BASE_URL}/api/trades`);
  return resp.json();
}

export async function fetchTrade(proposalId: string) {
  const resp = await fetch(`${BASE_URL}/api/trades/${proposalId}`);
  return resp.json();
}

export async function fetchReputation() {
  const resp = await fetch(`${BASE_URL}/api/reputation`);
  return resp.json();
}

export async function fetchPortfolio() {
  const resp = await fetch(`${BASE_URL}/api/portfolio`);
  return resp.json();
}
```

---

## Task 11: Chain Service (`dashboard/src/services/chain.ts`)

```typescript
/**
 * On-chain reputation reads via viem (Base Sepolia, read-only).
 */
import { createPublicClient, http } from "viem";
import { baseSepolia } from "viem/chains";

const REPUTATION_CONTRACT = import.meta.env.VITE_REPUTATION_CONTRACT as
  | `0x${string}`
  | undefined;

const client = createPublicClient({
  chain: baseSepolia,
  transport: http(),
});

export async function getOnChainTier(agentAddress: `0x${string}`) {
  if (!REPUTATION_CONTRACT) return null;
  // ABI for getTier(address) -> string
  const tier = await client.readContract({
    address: REPUTATION_CONTRACT,
    abi: [
      {
        name: "getTier",
        type: "function",
        stateMutability: "view",
        inputs: [{ name: "agent", type: "address" }],
        outputs: [{ name: "", type: "string" }],
      },
    ],
    functionName: "getTier",
    args: [agentAddress],
  });
  return tier;
}

export async function getOnChainScore(agentAddress: `0x${string}`) {
  if (!REPUTATION_CONTRACT) return null;
  const score = await client.readContract({
    address: REPUTATION_CONTRACT,
    abi: [
      {
        name: "getScore",
        type: "function",
        stateMutability: "view",
        inputs: [{ name: "agent", type: "address" }],
        outputs: [{ name: "", type: "uint256" }],
      },
    ],
    functionName: "getScore",
    args: [agentAddress],
  });
  return Number(score);
}
```

---

## Task 12: Chain Data Hook (`dashboard/src/hooks/useChainData.ts`)

```typescript
import { useEffect, useState } from "react";
import { getOnChainTier, getOnChainScore } from "../services/chain";

const AGENT_ADDRESS = import.meta.env.VITE_AGENT_ADDRESS as
  | `0x${string}`
  | undefined;

export function useChainData() {
  const [chainTier, setChainTier] = useState<string | null>(null);
  const [chainScore, setChainScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    if (!AGENT_ADDRESS) return;
    setLoading(true);
    try {
      const [tier, score] = await Promise.all([
        getOnChainTier(AGENT_ADDRESS),
        getOnChainScore(AGENT_ADDRESS),
      ]);
      setChainTier(tier as string | null);
      setChainScore(score);
    } catch {
      // Silently fail — on-chain data is optional
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return { chainTier, chainScore, loading, refresh };
}
```

---

## Task 13: Activity Feed Component

### 13a. `dashboard/src/components/ActivityFeed/FeedItem.tsx`

```tsx
import { useState } from "react";
import type { TrustDeskEvent } from "../../types";

const TYPE_COLORS: Record<string, string> = {
  proposal: "border-blue-500 bg-blue-950/30",
  verdict: "border-amber-500 bg-amber-950/30",
  execution: "border-green-500 bg-green-950/30",
  reputation_update: "border-yellow-500 bg-yellow-950/30",
  pass_decision: "border-gray-500 bg-gray-950/30",
  on_chain_confirmed: "border-emerald-500 bg-emerald-950/30",
};

function verdictColor(data: Record<string, unknown>): string {
  if (data.rejected) return "border-red-500 bg-red-950/30";
  if (data.modified) return "border-amber-500 bg-amber-950/30";
  return "border-green-500 bg-green-950/30";
}

function summaryLine(event: TrustDeskEvent): string {
  const d = event.data;
  switch (event.type) {
    case "proposal":
      return `New proposal: ${d.pair ?? "?"} ${d.side ?? ""} ${d.size ?? ""}`;
    case "verdict":
      return `Verdict: ${d.approved ? "APPROVED" : d.modified ? "MODIFIED" : "REJECTED"}`;
    case "execution":
      return `Execution: ${d.filled ? "FILLED" : "SKIPPED"}`;
    case "reputation_update":
      return `Tier change: ${d.from ?? "?"} → ${d.to ?? "?"}`;
    case "pass_decision":
      return `PASS: ${d.reason ?? "no opportunity"}`;
    case "on_chain_confirmed":
      return `On-chain confirmed: tx ${String(d.tx_hash ?? "").slice(0, 10)}...`;
    default:
      return event.type;
  }
}

export function FeedItem({ event }: { event: TrustDeskEvent }) {
  const [expanded, setExpanded] = useState(false);
  const colorClass =
    event.type === "verdict"
      ? verdictColor(event.data)
      : TYPE_COLORS[event.type] ?? "border-gray-500";

  const time = new Date(event.timestamp * 1000).toLocaleTimeString();

  return (
    <div
      className={`border-l-4 px-4 py-2 cursor-pointer rounded-r ${colorClass}`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex justify-between items-center">
        <span className="font-mono text-sm">{summaryLine(event)}</span>
        <span className="text-xs text-gray-400">{time}</span>
      </div>
      {expanded && (
        <pre className="mt-2 text-xs text-gray-300 overflow-x-auto">
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </div>
  );
}
```

### 13b. `dashboard/src/components/ActivityFeed/ActivityFeed.tsx`

```tsx
import type { TrustDeskEvent } from "../../types";
import { FeedItem } from "./FeedItem";

interface Props {
  events: TrustDeskEvent[];
}

export function ActivityFeed({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        Waiting for events...
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {events.map((event, i) => (
        <FeedItem key={`${event.timestamp}-${i}`} event={event} />
      ))}
    </div>
  );
}
```

### 13c. `dashboard/src/components/ActivityFeed/index.ts`

```typescript
export { ActivityFeed } from "./ActivityFeed";
```

---

## Task 14: Header Bar Component

### 14a. `dashboard/src/components/HeaderBar/HeaderBar.tsx`

```tsx
interface Props {
  tier: string;
  nav: number;
  unrealizedPnl: number;
  connected: boolean;
  mode?: "LIVE" | "PAPER";
}

const TIER_BADGES: Record<string, string> = {
  NOVICE: "bg-gray-600",
  EXPLORER: "bg-blue-600",
  STRATEGIST: "bg-purple-600",
  VETERAN: "bg-amber-600",
  ELITE: "bg-red-600",
};

export function HeaderBar({ tier, nav, unrealizedPnl, connected, mode = "PAPER" }: Props) {
  const badgeColor = TIER_BADGES[tier] ?? "bg-gray-600";
  const pnlColor = unrealizedPnl >= 0 ? "text-green-400" : "text-red-400";

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-700">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold text-white">TrustDesk</h1>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${badgeColor}`}>
          {tier}
        </span>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div>
          <span className="text-gray-400">NAV </span>
          <span className="text-white font-mono">${nav.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-gray-400">PnL </span>
          <span className={`font-mono ${pnlColor}`}>
            {unrealizedPnl >= 0 ? "+" : ""}{unrealizedPnl.toFixed(2)}
          </span>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-xs font-semibold ${
            mode === "LIVE" ? "bg-green-700 text-green-100" : "bg-yellow-700 text-yellow-100"
          }`}
        >
          {mode}
        </span>
        <span
          className={`h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`}
          title={connected ? "Connected" : "Disconnected"}
        />
      </div>
    </header>
  );
}
```

### 14b. `dashboard/src/components/HeaderBar/index.ts`

```typescript
export { HeaderBar } from "./HeaderBar";
```

---

## Task 15: PnL Panel Component

### 15a. `dashboard/src/components/PnLPanel/PnLPanel.tsx`

```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TrustDeskEvent } from "../../types";

interface Props {
  events: TrustDeskEvent[];
  nav: number;
  drawdownPct: number;
  wins: number;
  losses: number;
}

export function PnLPanel({ events, nav, drawdownPct, wins, losses }: Props) {
  // Build cumulative PnL from execution events
  const pnlData: { time: string; pnl: number }[] = [];
  let cumulative = 0;

  const executions = events
    .filter((e) => e.type === "execution" && e.data.pnl !== undefined)
    .reverse();

  for (const e of executions) {
    cumulative += Number(e.data.pnl ?? 0);
    pnlData.push({
      time: new Date((e.timestamp ?? 0) * 1000).toLocaleTimeString(),
      pnl: cumulative,
    });
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">PnL</h2>

      {pnlData.length > 0 ? (
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={pnlData}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#6b7280" />
            <YAxis tick={{ fontSize: 10 }} stroke="#6b7280" />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="pnl"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="text-gray-500 text-xs text-center py-6">
          No execution data yet
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 mt-3 text-center text-xs">
        <div>
          <div className="text-gray-400">NAV</div>
          <div className="text-white font-mono">${nav.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-gray-400">Drawdown</div>
          <div className="text-red-400 font-mono">{drawdownPct.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-gray-400">W / L</div>
          <div className="text-white font-mono">
            <span className="text-green-400">{wins}</span>
            {" / "}
            <span className="text-red-400">{losses}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### 15b. `dashboard/src/components/PnLPanel/index.ts`

```typescript
export { PnLPanel } from "./PnLPanel";
```

---

## Task 16: Reputation Panel Component

### 16a. `dashboard/src/components/ReputationPanel/ReputationPanel.tsx`

```tsx
interface Props {
  tier: string;
  score: number;
  totalTrades: number;
  successfulTrades: number;
  chainTier: string | null;
  chainScore: number | null;
  onVerify: () => void;
}

const TIER_ORDER = ["NOVICE", "EXPLORER", "STRATEGIST", "VETERAN", "ELITE"];

export function ReputationPanel({
  tier,
  score,
  totalTrades,
  successfulTrades,
  chainTier,
  chainScore,
  onVerify,
}: Props) {
  const tierIndex = TIER_ORDER.indexOf(tier);
  const progressPct = ((tierIndex + 1) / TIER_ORDER.length) * 100;
  const winRate = totalTrades > 0 ? ((successfulTrades / totalTrades) * 100).toFixed(1) : "0.0";

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Reputation</h2>

      {/* Tier progress */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>{tier}</span>
          <span>{TIER_ORDER[tierIndex + 1] ?? "MAX"}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Score summary */}
      <div className="grid grid-cols-2 gap-2 text-xs text-center mb-3">
        <div>
          <div className="text-gray-400">Score</div>
          <div className="text-white font-mono text-lg">{score}</div>
        </div>
        <div>
          <div className="text-gray-400">Win Rate</div>
          <div className="text-white font-mono text-lg">{winRate}%</div>
        </div>
      </div>

      {/* On-chain verification */}
      <div className="border-t border-gray-700 pt-3">
        <button
          onClick={onVerify}
          className="text-xs text-blue-400 hover:text-blue-300 underline"
        >
          Verify on-chain
        </button>
        {chainTier !== null && (
          <div className="mt-1 text-xs text-gray-400">
            Chain: {chainTier} (score: {chainScore})
          </div>
        )}
      </div>
    </div>
  );
}
```

### 16b. `dashboard/src/components/ReputationPanel/index.ts`

```typescript
export { ReputationPanel } from "./ReputationPanel";
```

---

## Task 17: App.tsx — Wire Everything Together

### `dashboard/src/App.tsx`

```tsx
import { useEffect, useState } from "react";
import { HeaderBar } from "./components/HeaderBar";
import { ActivityFeed } from "./components/ActivityFeed";
import { PnLPanel } from "./components/PnLPanel";
import { ReputationPanel } from "./components/ReputationPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { useChainData } from "./hooks/useChainData";
import { fetchReputation, fetchPortfolio } from "./services/websocket";
import type { Reputation, Portfolio } from "./types";

export default function App() {
  const { events, connected } = useWebSocket();
  const { chainTier, chainScore, refresh: refreshChain } = useChainData();

  const [reputation, setReputation] = useState<Reputation>({
    tier: "NOVICE",
    score: 0,
    total_trades: 0,
    successful_trades: 0,
    promotion_history: [],
  });

  const [portfolio, setPortfolio] = useState<Portfolio>({
    positions: [],
    nav: 10000,
    unrealized_pnl: 0,
  });

  // Fetch initial state
  useEffect(() => {
    fetchReputation().then(setReputation).catch(() => {});
    fetchPortfolio().then(setPortfolio).catch(() => {});
  }, []);

  // Update on reputation events
  useEffect(() => {
    const latest = events.find((e) => e.type === "reputation_update");
    if (latest) {
      fetchReputation().then(setReputation).catch(() => {});
    }
  }, [events]);

  // Compute PnL stats
  const executions = events.filter((e) => e.type === "execution");
  const wins = executions.filter((e) => Number(e.data.pnl ?? 0) > 0).length;
  const losses = executions.filter((e) => Number(e.data.pnl ?? 0) < 0).length;
  const drawdownPct = portfolio.nav > 0
    ? Math.max(0, -portfolio.unrealized_pnl / portfolio.nav) * 100
    : 0;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <HeaderBar
        tier={reputation.tier}
        nav={portfolio.nav}
        unrealizedPnl={portfolio.unrealized_pnl}
        connected={connected}
      />

      <div className="flex">
        {/* Main content — Activity Feed */}
        <main className="flex-1 p-4">
          <h2 className="text-sm font-semibold text-gray-400 mb-2">
            Activity Feed
          </h2>
          <ActivityFeed events={events} />
        </main>

        {/* Right sidebar — PnL + Reputation */}
        <aside className="w-80 p-4 space-y-4 border-l border-gray-800">
          <PnLPanel
            events={events}
            nav={portfolio.nav}
            drawdownPct={drawdownPct}
            wins={wins}
            losses={losses}
          />
          <ReputationPanel
            tier={reputation.tier}
            score={reputation.score}
            totalTrades={reputation.total_trades}
            successfulTrades={reputation.successful_trades}
            chainTier={chainTier}
            chainScore={chainScore}
            onVerify={refreshChain}
          />
        </aside>
      </div>
    </div>
  );
}
```

**Verify:** `cd dashboard && npm run build`

---

## Task 18: Dashboard main.tsx

### `dashboard/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**Verify:** `cd dashboard && npm run build`

---

## Task 19: Install Dashboard Dependencies

```bash
cd dashboard
npm install recharts viem
```

**Verify:** `npm run build` succeeds with no errors.

---

## Task 20: Full Backend Test Suite

Run all API tests together to confirm nothing is broken:

```bash
cd backend && python -m pytest src/trustdesk/api/tests/ -v --tb=short
```

Expected: all tests pass, no import errors, no fixture conflicts.

---

## Task 21: Full Dashboard Build Verification

```bash
cd dashboard && npm run build
```

Expected: build succeeds with no TypeScript errors and no warnings.

---

## Dependency Graph

```
Task 1  (EventBus)          — no dependencies
Task 2  (Health route)      — depends on Task 1 (app factory needs EventBus)
Task 3  (Trades route)      — depends on Task 2 (needs app factory)
Task 4  (Reputation route)  — depends on Task 2 (needs app factory)
Task 5  (WebSocket)         — depends on Task 1, Task 2
Task 6  (Integration tests) — depends on Tasks 1–5
Task 7  (__init__ files)    — depends on Tasks 1–5

Task 8  (Types)             — no dependencies
Task 9  (useWebSocket)      — depends on Task 8
Task 10 (websocket service) — depends on Task 8
Task 11 (chain service)     — depends on Task 19 (viem installed)
Task 12 (useChainData)      — depends on Task 11
Task 13 (ActivityFeed)      — depends on Task 8
Task 14 (HeaderBar)         — no dependencies
Task 15 (PnLPanel)          — depends on Task 8, Task 19 (recharts)
Task 16 (ReputationPanel)   — no dependencies
Task 17 (App.tsx)           — depends on Tasks 8–16
Task 18 (main.tsx)          — depends on Task 17
Task 19 (npm install)       — no dependencies

Task 20 (backend tests)     — depends on Tasks 1–7
Task 21 (dashboard build)   — depends on Tasks 8–19
```

### Parallelization groups:

- **Group A (parallel):** Tasks 1, 8, 14, 16, 19
- **Group B (parallel, after A):** Tasks 2, 9, 10, 11, 13
- **Group C (parallel, after B):** Tasks 3, 4, 5, 12, 15
- **Group D (parallel, after C):** Tasks 6, 7, 17
- **Group E (sequential, after D):** Task 18
- **Group F (parallel, after E):** Tasks 20, 21
