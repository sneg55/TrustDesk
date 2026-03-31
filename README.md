# TrustDesk

An AI trading desk that any agent can plug into — hard risk controls prevent blowups, on-chain reputation scores (ERC-8004) determine capital access, every trade executes through Kraken CLI with a verifiable audit trail.

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Kraken CLI](https://github.com/krakenfx/kraken-cli)
- [Foundry](https://book.getfoundry.sh/getting-started/installation)
- Node.js 20+
- Docker

### Setup

```bash
# 1. Clone and install
git clone <repo-url>
cd TrustDesk

# 2. Start PostgreSQL
docker compose up -d

# 3. Install Python dependencies
cd backend && uv sync --all-extras && cd ..

# 4. Install dashboard dependencies
cd dashboard && npm install && cd ..

# 5. Copy environment config
cp .env.example .env
# Edit .env with your API keys

# 6. Initialize database
cd backend && uv run python scripts/seed_db.py && cd ..
```

### Run

```bash
# Terminal 1: Main desk
cd backend && uv run python scripts/run_desk.py

# Terminal 2: Risk Manager (separate process)
cd backend && uv run python scripts/run_risk_manager.py

# Terminal 3: Dashboard
cd dashboard && npm run dev
```

### Test

```bash
cd backend && uv run pytest --cov --cov-report=term-missing  # all tests, 100% coverage
cd contracts && forge test                                     # contract tests
```

## Architecture

```
backend/src/trustdesk/
├── orchestrator/    # LangGraph state machine
├── signal_engine/   # Deterministic indicators + regime detection
├── strategist/      # Claude-powered trade proposals
├── risk_manager/    # Hard/soft limit checks (separate process)
├── auditor/         # ERC-8004 on-chain writes
├── reputation/      # Tier computation + promotion/demotion
├── adapters/        # Kraken CLI, Anthropic, web3, IPFS
├── schemas/         # Shared Pydantic models (the contract)
├── core/            # Config, errors, logging, DB, queue
└── api/             # FastAPI + WebSocket
```

See `CLAUDE.md` for development conventions and `TrustDesk_Product_Spec_v3.md` for the full spec.
