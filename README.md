# TrustDesk

**An AI trading desk that any agent can plug into.**

Hard risk controls prevent blowups. On-chain reputation scores (ERC-8004) determine how much capital each agent earns access to. Every trade executes through Kraken CLI with a verifiable audit trail on Base Sepolia.

Built for the [AI Trading Agents Hackathon](https://lablab.ai) (March 30 – April 12, 2026). Combined Kraken CLI + ERC-8004 submission.

---

## The Problem

Anyone can build a trading agent. Nobody can prove it won't blow up.

Past performance is self-reported. Backtests are curve-fitted. The only proof that matters is a verifiable track record with real money under real constraints, where every trade is auditable and every risk check is on the record.

## The Solution

TrustDesk is not a trading agent — it's a **trading desk that any agent can plug into**.

- **Agents bring strategy.** The desk controls what happens after.
- **New agents start small.** $100 allocation, 3% max position, 1 trade at a time.
- **Proven agents unlock more.** 20+ verified trades with positive PnL → $500 allocation, wider limits.
- **Blowups trigger automatic demotion.** No human in the loop. The on-chain record is the only input.

The desk doesn't care if the agent is an LLM, a rule-based script, or a reinforcement learning model. It only cares about results and risk behavior.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TRUSTDESK — DESK INFRASTRUCTURE                 │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    AGENT INTERFACE (API)                       │  │
│  │  Any agent connects here. Submit TradeProposal, receive       │  │
│  │  RiskVerdict, handle position lifecycle callbacks.            │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
│                              │                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              ORCHESTRATOR (LangGraph)                         │   │
│  │  signal → strategist → reputation → risk → execute → audit   │   │
│  └──────────┬──────────────┬──────────────────┬────────────────┘   │
│             │              │                  │                     │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐          │
│  │ RISK MANAGER  │  │   AUDITOR   │  │  REPUTATION      │          │
│  │ (separate     │  │ (on-chain   │  │  ENGINE          │          │
│  │  process,     │  │  writer)    │  │ (tier → limits)  │          │
│  │  own wallet)  │  │             │  │                  │          │
│  └──────────────┘  └─────────────┘  └──────────────────┘          │
└──────────────┬──────────────┬───────────────────┬─────────────────┘
               │              │                   │
    ┌──────────────┐  ┌───────────────┐  ┌──────────────┐
    │  KRAKEN CLI   │  │  ERC-8004     │  │  STRYKR/     │
    │  (paper/live) │  │  (Base        │  │  PRISM       │
    │              │  │   Sepolia)     │  │  (market     │
    │              │  │               │  │   intel)     │
    └──────────────┘  └───────────────┘  └──────────────┘
```

### Two-Process Model

| Process | What it runs | Wallet |
|---------|-------------|--------|
| **Desk** | Orchestrator, Signal Engine, Strategist, Auditor, API | Agent wallet (`0xABC`) |
| **Risk Manager** | Hard checks, soft checks, circuit breaker | Validator wallet (`0xDEF`) |

The Risk Manager runs as a **separate process with its own wallet**. On-chain, validation responses come from a different address than the agent — genuinely independent, as ERC-8004 intends.

---

## Reputation-Gated Capital

ERC-8004 reputation directly controls what an agent can do:

| Tier | Entry Criteria | Capital | Max Position | Max Trades | Max Daily Loss |
|------|---------------|---------|-------------|-----------|---------------|
| **Unproven** | New agent | $100 | 3% | 1 | 3% |
| **Established** | 20+ trades, PnL > 0, DD < 15% | $500 | 7% | 3 | 5% |
| **Trusted** | 50+ trades, equity rising 60%+, DD < 10% | $1,000+ | 10% | 5 | 5% |

Promotion is automatic after verified trades. Demotion is immediate on drawdown breach or 5 consecutive losses. 5-trade cooldown before re-promotion.

---

## Risk Manager

### Hard Checks (deterministic, non-negotiable)
1. Position size ≤ tier max
2. Total open exposure ≤ 40%
3. Daily realized loss ≤ tier max
4. Max open positions ≤ tier max
5. Min 30 minutes between trades on same pair

### Soft Checks (LLM-evaluated via Claude)
1. Correlation check (correlated exposure < 60%)
2. Regime alignment (proposal matches market regime)
3. Drawdown headroom (room before -15% max DD)
4. Invalidation plausibility
5. Alignment score calibration
6. Override scrutiny

### Circuit Breaker
When Anthropic API is unavailable, the Risk Manager switches to **hard-limits-only mode**. Soft checks are skipped. Trades are flagged `APPROVED_HARD_ONLY` on-chain.

### Adaptive Parameters
- 3 consecutive losses → tighten position limits
- Drawdown > 3% → require STRONG alignment only
- Drawdown > 8% → no new trades
- Regime shift to VOLATILE → halve all soft limits

---

## Signal Engine

Deterministic Python service — **no LLM**. Ingests market data from Kraken CLI + Strykr/PRISM and outputs structured `SignalPayload` objects.

**Indicators** (pure pandas, no ta-lib C dependency):
- Trend: EMA 9/21/50, crossover state, ADX
- Momentum: RSI, Stochastic RSI, Rate of Change
- Volatility: ATR, Bollinger Bands, Keltner Channel
- Volume: Volume SMA ratio, OBV, VWAP
- Market structure: Order book imbalance, trade flow, spread

**Regime Detection:**
- `TRENDING_UP` — ADX > 25, EMA 9 > 21 > 50, OBV rising
- `TRENDING_DOWN` — ADX > 25, EMA 9 < 21 < 50, OBV falling
- `RANGING` — ADX < 20, Bollinger squeezing
- `VOLATILE` — ATR > 2x average, Bollinger expanding

**Signal Alignment Score** — 5-signal deterministic agreement count:

| Score | Grade | Position Size |
|-------|-------|--------------|
| 5/5 | STRONG | 10% |
| 4/5 | MODERATE | 8% |
| 3/5 | WEAK | 5% (override required) |
| ≤2/5 | NO_SIGNAL | 0% (PASS) |

---

## Dual-Path Validation

```
FAST PATH (sub-second)              TRUST PATH (async, on-chain)
Proposal → Risk Manager             ┌─ IPFS upload (proposal)
         ↓                          ├─ validationRequest() [agent wallet]
    Verdict (local)                 ├─ IPFS upload (verdict)
         ↓                          └─ validationResponse() [validator wallet]
  Execute / Skip                              ↓
         ↓                          On-chain record confirmed
  Dashboard: "Executed"             Dashboard: "On-chain"
```

Trades execute immediately via the fast path. The trust path posts the full audit trail to ERC-8004 asynchronously. Both states visible in the dashboard.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Signal Engine | Python 3.11, pandas |
| Orchestration | LangGraph (state machine) |
| LLM | Claude Sonnet 4 (Anthropic API) |
| Kraken Integration | [Kraken CLI](https://github.com/krakenfx/kraken-cli) (MCP + subprocess) |
| Market Intelligence | [Strykr/PRISM](https://prismapi.ai) (asset resolution, AI signals, risk metrics) |
| Smart Contracts | Foundry, Solidity 0.8.24 (Base Sepolia) |
| On-chain Interaction | web3.py (backend) + viem (dashboard) |
| IPFS | Pinata |
| Dashboard | React + Tailwind + Recharts + WebSocket |
| Database | PostgreSQL 16 (Docker) |
| API | FastAPI + uvicorn |
| Testing | pytest (562 tests, 100% coverage) + forge (7 tests) |

---

## Quick Start

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- [Kraken CLI](https://github.com/krakenfx/kraken-cli) (`curl --proto '=https' --tlsv1.2 -LsSf https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh`)
- [Foundry](https://book.getfoundry.sh/getting-started/installation) (`curl -L https://foundry.paradigm.xyz | bash`)
- Node.js 20+
- Docker

### Setup

```bash
# Clone
git clone https://github.com/sneg55/TrustDesk.git
cd TrustDesk

# Start PostgreSQL
docker compose up -d

# Install Python dependencies
cd backend && uv sync --all-extras && cd ..

# Install dashboard dependencies
cd dashboard && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env — add your API keys (see below)
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TRUSTDESK_MODE` | No | `paper` (default) or `live` |
| `ANTHROPIC_API_KEY` | For LLM | Claude Sonnet 4 for strategist + soft checks |
| `PRISM_API_KEY` | For signals | Strykr/PRISM market intelligence |
| `KRAKEN_API_KEY` | For live trading | Kraken API key (paper trading needs none) |
| `KRAKEN_API_SECRET` | For live trading | Kraken API secret |
| `TRUSTDESK_AGENT_PRIVATE_KEY` | For on-chain | Agent wallet private key (Base Sepolia) |
| `TRUSTDESK_VALIDATOR_PRIVATE_KEY` | For on-chain | Validator wallet private key (Base Sepolia) |
| `PINATA_API_KEY` | For IPFS | Pinata API key for decision records |
| `DATABASE_URL` | No | PostgreSQL URL (defaults to local Docker) |

The system degrades gracefully — if a key isn't set, that adapter is disabled and the desk continues with reduced functionality.

### Run

```bash
# Terminal 1: Start the desk
cd backend && uv run python scripts/run_desk.py

# Terminal 2: Start Risk Manager (separate process, separate wallet)
cd backend && uv run python scripts/run_risk_manager.py

# Terminal 3: Start dashboard
cd dashboard && npm run dev
```

- **API:** http://localhost:8000
- **Dashboard:** http://localhost:5175
- **Health check:** http://localhost:8000/health

### Test

```bash
# Python — 562 tests, 100% coverage enforced
cd backend && uv run pytest --cov --cov-report=term-missing

# Contracts — 7 forge tests
cd contracts && forge test

# Lint
cd backend && uv run ruff check src/

# Dashboard build
cd dashboard && npm run build
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check + version |
| `GET` | `/api/trades` | Trade history |
| `GET` | `/api/trades/{id}` | Single trade detail |
| `GET` | `/api/reputation` | Current tier, score, promotion history |
| `WS` | `/ws` | Real-time event stream |

WebSocket events: `proposal`, `verdict`, `execution`, `reputation_update`, `pass_decision`, `on_chain_confirmed`

---

## Smart Contracts

### TrustDeskOpenValidator

Permissionless validation — **anyone** can post an assessment of any TrustDesk trade.

```solidity
function validateTrade(
    uint256 agentId,
    bytes32 requestHash,
    bool approved,
    string calldata reason,
    string calldata evidenceURI
) external
```

Deployed to Base Sepolia. Wraps ERC-8004 Validation Registry. Emits `TradeValidated` events for dashboard consumption.

```bash
# Build
cd contracts && forge build

# Test
cd contracts && forge test -vvv

# Deploy
forge script script/Deploy.s.sol --rpc-url $BASE_SEPOLIA_RPC --broadcast
```

---

## Project Structure

```
TrustDesk/
├── backend/
│   ├── src/trustdesk/
│   │   ├── orchestrator/       # LangGraph pipeline
│   │   ├── signal_engine/      # Indicators, regime, alignment (pandas)
│   │   ├── strategist/         # Claude-powered trade decisions
│   │   ├── risk_manager/       # Hard/soft checks, circuit breaker, adaptive
│   │   ├── auditor/            # On-chain writes, IPFS, PASS logging, retry
│   │   ├── reputation/         # Tier computation, promotion/demotion
│   │   ├── adapters/
│   │   │   ├── kraken/         # Kraken CLI (MCP + subprocess)
│   │   │   ├── anthropic/      # Claude Sonnet 4 (circuit breaker)
│   │   │   ├── chain/          # web3.py + ERC-8004 registries + gas monitor
│   │   │   ├── ipfs/           # Pinata upload/pin
│   │   │   └── strykr/         # PRISM asset resolution, signals, risk
│   │   ├── schemas/            # Shared Pydantic models
│   │   ├── core/               # Config, errors, logging, DB, queue
│   │   └── api/                # FastAPI REST + WebSocket
│   ├── scripts/                # Entry points (run_desk, run_risk_manager)
│   └── pyproject.toml
├── contracts/                  # Foundry (TrustDeskOpenValidator.sol)
├── dashboard/                  # Vite + React + Tailwind + Recharts
├── docs/                       # Design specs + implementation plans
├── docker-compose.yml          # PostgreSQL
├── CLAUDE.md                   # AI development conventions
└── .env.example                # All environment variables documented
```

---

## What Makes This Win

1. **It's a platform, not a bot.** Every other team submits a trading agent. TrustDesk submits the infrastructure that makes any agent safe to deploy.

2. **Reputation = capital access.** On-chain reputation directly controls how much capital an agent gets. ERC-8004 is load-bearing, not decorative.

3. **The Risk Manager is genuinely external.** Separate wallet, separate process, on-chain validation from a different address.

4. **Dual-path validation mirrors real trading desks.** Fast local execution + async on-chain attestation.

5. **Every failure mode degrades gracefully.** LLM down → hard-limits-only. MCP down → subprocess fallback. Gas low → tiered write priority. Process crash → exchange-side stops.

6. **562 tests, 100% coverage.** Every line of business logic is tested.

---

## License

MIT
