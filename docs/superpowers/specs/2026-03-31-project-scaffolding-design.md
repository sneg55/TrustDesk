# TrustDesk — Project Scaffolding Design

**Date:** 2026-03-31
**Status:** Approved
**Context:** AI Trading Agents Hackathon (March 30 – April 12, 2026), combined Kraken CLI + ERC-8004 submission

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo structure | Monorepo (`backend/`, `contracts/`, `dashboard/`) | Single git history, easier coordination during hackathon |
| On-chain library | web3.py (backend writes) + viem (dashboard reads) | Each tool used where it's strongest |
| Python package manager | uv | Fastest install times, good lockfile support |
| Database | PostgreSQL via Docker Compose | Concurrent access needed (retry queues, state reconciliation) |
| Dashboard | Vite + React + Tailwind + Recharts | Pure client-side SPA, no SSR needed |
| Kraken CLI | Assume pre-installed, adapter interface | Paper trading needs no API keys, built-in MCP server, designed for AI agents |
| AI-driven dev approach | Hybrid single-package with standardized module internals | Small files, co-located tests, one schema per file, parallel agent work |
| Market intelligence | Strykr/PRISM API for asset resolution, signals, and risk metrics | Hackathon sponsor tool, free credits, 20+ data sources, enhances signal quality |

---

## Directory Structure

```
TrustDesk/
├── backend/
│   ├── src/trustdesk/
│   │   ├── __init__.py
│   │   ├── orchestrator/              # LangGraph state machine
│   │   │   ├── __init__.py
│   │   │   ├── graph.py               # LangGraph graph definition
│   │   │   ├── nodes.py               # Graph nodes (proposal, validate, execute, log)
│   │   │   ├── state.py               # Graph state schema
│   │   │   ├── lifecycle.py           # Position lifecycle callbacks
│   │   │   ├── types.py
│   │   │   ├── constants.py
│   │   │   └── tests/
│   │   │
│   │   ├── signal_engine/             # Deterministic computation (no LLM)
│   │   │   ├── __init__.py
│   │   │   ├── engine.py              # Main cycle: ingest → compute → output payload
│   │   │   ├── indicators.py          # EMA, RSI, ADX, ATR, Bollinger, etc.
│   │   │   ├── regime.py              # TRENDING_UP/DOWN, RANGING, VOLATILE detection
│   │   │   ├── alignment.py           # Signal Alignment Score (5-signal deterministic)
│   │   │   ├── market_structure.py    # Order book imbalance, trade flow, spread
│   │   │   ├── types.py
│   │   │   ├── constants.py
│   │   │   └── tests/
│   │   │
│   │   ├── strategist/                # Demo agent's LLM decision-maker
│   │   │   ├── __init__.py
│   │   │   ├── strategist.py          # Interpret signals → TradeProposal or PASS
│   │   │   ├── prompts.py             # System prompt, regime-specific prompts
│   │   │   ├── cycle.py               # Cycle frequency logic per regime
│   │   │   ├── types.py
│   │   │   ├── constants.py
│   │   │   └── tests/
│   │   │
│   │   ├── risk_manager/              # External validator (separate process)
│   │   │   ├── __init__.py
│   │   │   ├── manager.py             # Main evaluation pipeline
│   │   │   ├── hard_checks.py         # 5 deterministic hard limits
│   │   │   ├── soft_checks.py         # 6 LLM-evaluated soft limits
│   │   │   ├── circuit_breaker.py     # LLM unavailable → hard-limits-only mode
│   │   │   ├── adaptive.py            # Parameter adjustments (3 losses → tighten, etc.)
│   │   │   ├── types.py
│   │   │   ├── constants.py
│   │   │   └── tests/
│   │   │
│   │   ├── auditor/                   # Deterministic on-chain writer
│   │   │   ├── __init__.py
│   │   │   ├── auditor.py             # Main logging pipeline
│   │   │   ├── reputation_lifecycle.py # 3-stage: trade_open → trade_update → trade_close
│   │   │   ├── pass_logger.py         # Rate-limited PASS summaries (1/hour/regime)
│   │   │   ├── ipfs.py                # IPFS upload logic
│   │   │   ├── types.py
│   │   │   ├── constants.py
│   │   │   └── tests/
│   │   │
│   │   ├── reputation/                # Reputation-to-limits engine
│   │   │   ├── __init__.py
│   │   │   ├── engine.py              # Compute tier from on-chain feedback
│   │   │   ├── tiers.py               # Tier definitions, limits mapping
│   │   │   ├── promotion.py           # Promotion/demotion logic, cooldowns
│   │   │   ├── types.py
│   │   │   ├── constants.py
│   │   │   └── tests/
│   │   │
│   │   ├── adapters/                  # External service interfaces
│   │   │   ├── __init__.py
│   │   │   ├── kraken/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py          # Unified interface (MCP → subprocess fallback)
│   │   │   │   ├── mcp.py             # MCP client
│   │   │   │   ├── subprocess.py      # Subprocess fallback
│   │   │   │   ├── types.py
│   │   │   │   └── tests/
│   │   │   ├── anthropic/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py          # Claude Sonnet 4 wrapper
│   │   │   │   └── tests/
│   │   │   ├── chain/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py          # web3.py ERC-8004 calls
│   │   │   │   ├── identity.py        # Identity Registry
│   │   │   │   ├── reputation.py      # Reputation Registry (giveFeedback)
│   │   │   │   ├── validation.py      # Validation Registry (request/response)
│   │   │   │   ├── gas_monitor.py     # Balance check, tiered write priority
│   │   │   │   └── tests/
│   │   │   ├── ipfs/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py          # Pinata upload, pin management
│   │   │   │   └── tests/
│   │   │   └── strykr/
│   │   │       ├── __init__.py
│   │   │       ├── client.py          # PRISM API: resolve, signals, risk
│   │   │       ├── types.py           # ResolvedAsset, PrismSignal, PrismRisk
│   │   │       └── tests/
│   │   │
│   │   ├── schemas/                   # Shared Pydantic models (one per file)
│   │   │   ├── __init__.py
│   │   │   ├── proposal.py            # TradeProposal
│   │   │   ├── verdict.py             # RiskVerdict
│   │   │   ├── signal_payload.py      # SignalPayload, AlignmentScore
│   │   │   ├── reputation.py          # ReputationFeedback, TierChange
│   │   │   ├── callbacks.py           # Position lifecycle callbacks
│   │   │   └── agent_interface.py     # AgentRegistration, MarketDataFeed
│   │   │
│   │   ├── core/                      # Shared infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── errors.py              # Error hierarchy, safe extraction
│   │   │   ├── config.py              # Centralized env/config (never raw os.environ)
│   │   │   ├── logging.py             # Structured logging with correlation IDs
│   │   │   ├── constants.py           # Global constants, error IDs
│   │   │   ├── db.py                  # PostgreSQL connection, session factory
│   │   │   └── queue.py              # Internal message queue (proposal → verdict)
│   │   │
│   │   └── api/                       # FastAPI application
│   │       ├── __init__.py
│   │       ├── app.py                 # FastAPI app factory
│   │       ├── websocket.py           # WebSocket endpoints for dashboard
│   │       ├── routes/
│   │       │   ├── health.py
│   │       │   ├── trades.py
│   │       │   └── reputation.py
│   │       └── tests/
│   │
│   ├── scripts/
│   │   ├── run_desk.py                # Main entry: orchestrator + signal engine + strategist + auditor
│   │   ├── run_risk_manager.py        # Separate process: risk manager with own wallet
│   │   ├── run_backtest.py            # Backtest runner
│   │   └── seed_db.py                 # DB schema setup
│   │
│   ├── migrations/                    # Alembic
│   ├── pyproject.toml
│   └── uv.lock
│
├── contracts/
│   ├── src/
│   │   └── TrustDeskOpenValidator.sol
│   ├── test/
│   │   └── TrustDeskOpenValidator.t.sol
│   ├── script/
│   │   └── Deploy.s.sol
│   └── foundry.toml
│
├── dashboard/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ActivityFeed/          # Tier 1: desk activity feed
│   │   │   ├── HeaderBar/             # NAV, PnL, LIVE/PAPER badge
│   │   │   ├── PnLPanel/             # Tier 2: cumulative PnL chart
│   │   │   ├── ReputationPanel/       # Tier 2: tier badge, progress, history
│   │   │   └── TradeReplay/           # Tier 3: trade timeline view
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts        # WebSocket connection to backend
│   │   │   └── useChainData.ts        # viem read-only chain queries
│   │   ├── services/
│   │   │   ├── websocket.ts
│   │   │   └── chain.ts              # viem client setup
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── vite.config.ts
│
├── docker-compose.yml                 # PostgreSQL
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md
├── CLAUDE.local.md
└── .claude/
    └── rules/
        ├── testing.md
        ├── git-workflow.md
        ├── code-style.md
        └── security.md
```

---

## Schemas — The Shared Contract

Pydantic models that define the interface between all modules. One file per schema.

### TradeProposal (`schemas/proposal.py`)

```python
class TradeProposal(BaseModel):
    agent_id: str
    proposal_id: str
    timestamp: datetime
    action: Literal["BUY", "SELL"]
    pair: str                          # e.g. "BTC/USD"
    size_pct: float                    # % of agent's allocated capital
    entry_price_limit: float
    entry_type: Literal["LIMIT"]
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None
    time_horizon: str                  # e.g. "4h", "24h"
    reasoning: str
    invalidation: str
    # Optional enrichment from signal-aware agents
    alignment_score: float | None = None
    alignment_grade: Literal["STRONG", "MODERATE", "WEAK", "NO_SIGNAL"] | None = None
    override_justification: str | None = None
    regime_at_proposal: Literal["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"] | None = None
    signals_cited: list[str] | None = None
```

### RiskVerdict (`schemas/verdict.py`)

```python
class FieldModification(BaseModel):
    original: float
    approved: float
    reason: str

class RiskVerdict(BaseModel):
    proposal_id: str
    validator_address: str
    verdict: Literal["APPROVED", "APPROVED_WITH_MODIFICATION", "APPROVED_HARD_ONLY", "REJECTED"]
    tier_at_verdict: Literal["UNPROVEN", "ESTABLISHED", "TRUSTED"]
    modifications: dict[str, FieldModification] | None = None
    hard_checks: dict[str, str]        # check_name → "PASS (...)" or "FAIL (...)"
    soft_checks: dict[str, str] | Literal["SKIPPED_LLM_UNAVAILABLE"]
    reasoning: str
    evidence_uri: str | None = None
    on_chain_tx: str | None = None
```

### SignalPayload (`schemas/signal_payload.py`)

```python
class AlignmentBreakdown(BaseModel):
    ema_direction: bool
    adx_strength: bool
    volume_confirmation: bool
    obv_trend_match: bool
    book_imbalance_favorable: bool

class Alignment(BaseModel):
    score: float                       # 0.0 - 1.0
    grade: Literal["STRONG", "MODERATE", "WEAK", "NO_SIGNAL"]
    signals_agreeing: int
    signals_total: int = 5
    breakdown: AlignmentBreakdown

class DerivedValues(BaseModel):
    suggested_stop_distance: float
    position_size_pct: float
    regime_aligned: bool

class SignalPayload(BaseModel):
    timestamp: datetime
    pair: str
    price: float
    regime: Literal["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"]
    regime_confidence: float
    regime_changed: bool
    signals: dict[str, Any]
    alignment: Alignment
    derived: DerivedValues
```

### ReputationFeedback (`schemas/reputation.py`)

```python
class ReputationFeedback(BaseModel):
    type: Literal["TRADE_OPENED", "TRADE_UPDATE", "TRADE_CLOSED", "PASS_SUMMARY", "RISK_ADJUST"]
    score: int                         # 0-100, 50 = neutral
    tag: str                           # trade_open, trade_update, trade_close, no_trade, risk_adjust
    skill: str                         # pair or "MARKET_OVERVIEW" or "RISK"
    evidence_uri: str
    context: dict[str, Any]

class TierDefinition(BaseModel):
    tier: Literal["UNPROVEN", "ESTABLISHED", "TRUSTED"]
    capital_allocation: float
    max_position_pct: float
    max_open_trades: int
    max_daily_loss_pct: float
```

### PositionCallback (`schemas/callbacks.py`)

```python
class PositionCallback(BaseModel):
    event: Literal["FILLED", "PARTIAL_EXIT", "STOP_TRIGGERED", "TIME_EXIT", "INVALIDATION_EXIT", "DEMOTION"]
    proposal_id: str
    timestamp: datetime
    details: dict[str, Any]
```

---

## Module Responsibilities

| Module | Owns | Depends on |
|--------|------|------------|
| `signal_engine` | Indicator calculations, regime detection, alignment score, signal payloads | `adapters/kraken` |
| `strategist` | Trade decision logic, prompts, cycle frequency | `adapters/anthropic`, `schemas` |
| `risk_manager` | Hard checks, soft checks, circuit breaker, adaptive params, verdicts | `adapters/anthropic`, `adapters/kraken`, `reputation` |
| `orchestrator` | LangGraph graph, node sequencing, execution flow, position lifecycle | All modules (wires them together) |
| `auditor` | IPFS uploads, ERC-8004 writes, PASS rate-limiting, retry queue | `adapters/chain`, `adapters/ipfs` |
| `reputation` | Tier computation from on-chain data, promotion/demotion, cooldowns | `adapters/chain` |
| `adapters/kraken` | MCP + subprocess dual-path, unified JSON interface | Kraken CLI binary |
| `adapters/chain` | web3.py calls, gas monitoring, tiered write priority | Base Sepolia RPC |
| `adapters/ipfs` | Pinata uploads, pin management, CID storage | Pinata API |
| `adapters/anthropic` | Claude Sonnet 4 calls, structured output parsing | Anthropic API |
| `adapters/strykr` | PRISM asset resolution, AI signals, risk metrics | Strykr/PRISM API |
| `core` | Config, errors, logging, DB, internal queue | PostgreSQL |
| `api` | FastAPI app, WebSocket streaming to dashboard | `core/db`, event bus |

### Data Flow

```
Signal Engine → SignalPayload → Strategist → TradeProposal → Orchestrator
                                                                   │
                                              ┌────────────────────┼──────────────┐
                                              ▼                    ▼              ▼
                                        Risk Manager          Reputation      Auditor
                                        (separate process)    Engine          (async)
                                              │                    │              │
                                              ▼                    ▼              ▼
                                        RiskVerdict           TierDefinition  ERC-8004 +
                                              │                                  IPFS
                                              ▼
                                        Kraken CLI
                                        (execute/skip)
```

### Process Separation

- `scripts/run_desk.py`: orchestrator + signal_engine + strategist + auditor + api (one async process)
- `scripts/run_risk_manager.py`: risk_manager only (separate process, validator wallet)
- Communication: PostgreSQL-backed message queue (`core/queue.py`)
- Channels: `proposals` (desk → risk_manager), `verdicts` (risk_manager → desk)

### Dual-Path Validation

1. Proposal enters queue → Risk Manager picks up (fast path, sub-second)
2. Risk Manager returns verdict → Orchestrator executes or skips
3. Auditor posts proposal + verdict to IPFS + ERC-8004 (trust path, async, 15-60s)
4. Dashboard shows both: "Executed" immediately, "On-chain" when confirmed

---

## Adapters

### Kraken (`adapters/kraken/client.py`)

Unified interface. MCP primary, subprocess fallback. Reads `TRUSTDESK_MODE` — `paper` uses `kraken paper buy`, `live` uses `kraken order buy`.

```python
class KrakenClient:
    async def ticker(self, pair: str) -> TickerData
    async def ohlc(self, pair: str, interval: int) -> list[Candle]
    async def orderbook(self, pair: str, count: int) -> OrderBook
    async def recent_trades(self, pair: str) -> list[Trade]
    async def balance(self) -> dict[str, float]
    async def open_orders(self) -> list[Order]
    async def place_order(self, side: str, pair: str, volume: float,
                          price: float, order_type: str = "limit") -> OrderResult
    async def cancel_order(self, order_id: str) -> bool
    async def trade_history(self) -> list[TradeRecord]
```

### Chain (`adapters/chain/client.py`)

web3.py for Base Sepolia. Two wallets: agent (0xABC) for identity + reputation, validator (0xDEF) for validation responses.

```python
class ChainClient:
    async def register_agent(self, metadata: dict) -> str
    async def give_feedback(self, agent_id: int, score: int,
                            tag: str, skill: str, evidence_uri: str) -> str
    async def validation_request(self, validator_addr: str, agent_id: int,
                                 request_uri: str, request_hash: bytes) -> str
    async def validation_response(self, request_hash: bytes, approved: bool,
                                  response_uri: str, response_hash: bytes,
                                  tags: str) -> str
    async def check_balance(self, wallet: str) -> float
    def get_write_priority(self, balance: float) -> WritePriority
```

### Gas Monitor (`adapters/chain/gas_monitor.py`)

Background task, every 30 minutes. Tiered write priority:

| Balance | Priority | What gets written |
|---------|----------|-------------------|
| > 0.1 ETH | NORMAL | Everything |
| 0.05-0.1 | REDUCED | Trade open/close + validation only |
| 0.01-0.05 | CRITICAL | Trade close + validation response only |
| < 0.01 | EMERGENCY | Queue all, attempt faucet refill |

### Anthropic (`adapters/anthropic/client.py`)

Claude Sonnet 4 for Strategist and Risk Manager soft checks. Circuit breaker: when unavailable, Strategist skips cycle, Risk Manager uses hard-limits-only mode.

```python
class AnthropicClient:
    async def strategist_evaluate(self, signal_payload: SignalPayload,
                                   portfolio_state: dict) -> TradeProposal | None
    async def risk_evaluate_soft(self, proposal: TradeProposal,
                                  portfolio_state: dict) -> SoftCheckResults
    def is_available(self) -> bool
```

### IPFS (`adapters/ipfs/client.py`)

Pinata for decision records. Pin for persistence.

```python
class IPFSClient:
    async def upload_json(self, data: dict, name: str) -> str
    async def verify_pin(self, cid: str) -> bool
    async def repin_if_needed(self, cids: list[str]) -> list[str]
```

### Strykr/PRISM (`adapters/strykr/client.py`)

Hackathon sponsor market intelligence API. 20+ data sources, sub-100ms latency. PRISM resolves any asset identifier to a canonical identity. Provides AI signals and risk metrics as supplementary data for the Signal Engine and Risk Manager.

```python
class StrykrClient:
    async def resolve(self, symbol: str) -> ResolvedAsset    # Canonical asset identity + venues
    async def signals(self, symbol: str) -> PrismSignal      # AI signals: direction, strength, RSI, MACD, Bollinger
    async def risk(self, symbol: str) -> PrismRisk            # Volatility, Sharpe, Sortino, drawdown metrics
    async def close(self) -> None
```

Integration points:
- **Orchestrator**: resolve agent-submitted symbols via PRISM before passing to Kraken
- **Signal Engine**: `/signals/{symbol}` as supplementary alignment data (external AI consensus)
- **Risk Manager**: `/risk/{symbol}` for external volatility and drawdown cross-checks

---

## Core Infrastructure

### Config (`core/config.py`)

Single source of truth. Never use `os.environ` directly. Loaded once at startup, passed via dependency injection.

Key settings:
- `mode`: paper/live
- Kraken: API key/secret, MCP toggle
- Anthropic: API key, model name
- Chain: RPC URL, agent wallet key, validator wallet key, contract addresses
- IPFS: Pinata key/secret
- Database: connection URL
- Tuning: gas check interval, signal interval

### Errors (`core/errors.py`)

```python
class TrustDeskError(Exception): ...
class KrakenError(TrustDeskError): ...
class ChainError(TrustDeskError): ...
class LLMUnavailableError(TrustDeskError): ...
class IPFSError(TrustDeskError): ...
class ValidationError(TrustDeskError): ...
class RiskCheckFailed(TrustDeskError): ...
```

### Logging (`core/logging.py`)

structlog with correlation IDs per orchestrator cycle. Every log entry carries `correlation_id` and `module` for trace filtering.

### Database (`core/db.py`)

PostgreSQL via SQLAlchemy async + asyncpg. Tables: `trades`, `signals`, `reputation_events`, `retry_queue`, `agent_sessions`. Migrations via Alembic.

### Queue (`core/queue.py`)

PostgreSQL-backed message queue. Channels: `proposals`, `verdicts`. Survives process restarts.

---

## Entry Points

| Script | What it runs | Wallet |
|--------|-------------|--------|
| `run_desk.py` | Orchestrator + Signal Engine + Strategist + Auditor + FastAPI | Agent (0xABC) |
| `run_risk_manager.py` | Risk Manager only | Validator (0xDEF) |
| `run_backtest.py` | Historical Signal Engine + simulated Strategist + hard checks | None |
| `seed_db.py` | Create tables, run migrations | None |

### Docker Compose

PostgreSQL only. Python processes run locally via `uv run`. Dashboard via `npm run dev`.

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: trustdesk
      POSTGRES_USER: trustdesk
      POSTGRES_PASSWORD: trustdesk
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

### Dev Startup

```bash
docker compose up -d                          # PostgreSQL
uv run python scripts/run_desk.py             # Terminal 1: main desk
uv run python scripts/run_risk_manager.py     # Terminal 2: risk manager
cd dashboard && npm run dev                   # Terminal 3: dashboard
```

---

## Dependencies

### Python (`pyproject.toml`)

| Package | Purpose |
|---------|---------|
| langgraph | Orchestrator state machine |
| anthropic | Claude Sonnet 4 API |
| fastapi + uvicorn | HTTP + WebSocket server |
| websockets | WebSocket support |
| pandas | Signal Engine data manipulation |
| pandas (replaces TA-Lib) | Technical indicator calculations (pure Python, no C dependency) |
| web3 | ERC-8004 on-chain calls |
| sqlalchemy[asyncio] + asyncpg | PostgreSQL async |
| alembic | Database migrations |
| pydantic | Schema validation |
| structlog | Structured logging |
| httpx | Pinata + Strykr/PRISM API calls |
| ruff | Linting + formatting (dev) |
| pytest + pytest-asyncio | Testing (dev) |

### Dashboard (`package.json`)

| Package | Purpose |
|---------|---------|
| react + react-dom | UI |
| viem | Read-only chain queries |
| recharts | PnL charts |
| tailwindcss | Styling |
| typescript | Type safety |
| eslint + prettier | Linting (dev) |

### Contracts (`foundry.toml`)

Foundry defaults + OpenZeppelin for ERC-8004 interface imports.

---

## CLAUDE.md Summary

Project-wide CLAUDE.md includes:
- Architecture overview (two-process model)
- All build/test/lint commands for backend, contracts, dashboard
- Code style rules (ruff, strict TS, naming conventions)
- Architecture rules: adapters boundary, schemas as contract, no cross-module imports
- What not to do: no logic in adapters, no raw os.environ, no 300+ line files

Additional `.claude/rules/` files: testing.md, git-workflow.md, code-style.md, security.md.

---

## .env.example

```bash
TRUSTDESK_MODE=paper
KRAKEN_API_KEY=
KRAKEN_API_SECRET=
TRUSTDESK_KRAKEN_MCP=true
ANTHROPIC_API_KEY=
TRUSTDESK_RPC_URL=https://sepolia.base.org
TRUSTDESK_AGENT_PRIVATE_KEY=
TRUSTDESK_VALIDATOR_PRIVATE_KEY=
TRUSTDESK_IDENTITY_REGISTRY=
TRUSTDESK_REPUTATION_REGISTRY=
TRUSTDESK_VALIDATION_REGISTRY=
TRUSTDESK_OPEN_VALIDATOR=
PINATA_API_KEY=
PINATA_API_SECRET=
PRISM_API_KEY=
DATABASE_URL=postgresql+asyncpg://trustdesk:trustdesk@localhost:5433/trustdesk
TRUSTDESK_GAS_CHECK_INTERVAL=1800
TRUSTDESK_SIGNAL_INTERVAL=300
TRUSTDESK_LLM_MODEL=claude-sonnet-4-20250514
```
