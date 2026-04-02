# TrustDesk

AI trading desk — any agent plugs in, risk controls prevent blowups,
on-chain reputation (ERC-8004) determines capital access.

Hackathon: AI Trading Agents (March 30 – April 12, 2026)
Combined submission: Kraken CLI + ERC-8004

## Architecture

- `backend/src/trustdesk/` — Python 3.11, LangGraph, FastAPI
- `contracts/` — Foundry, Solidity (Base Sepolia)
- `dashboard/` — Vite + React + Tailwind + Recharts

Two processes:
- **Desk** (orchestrator + signal engine + strategist + auditor + api)
- **Risk Manager** (separate process, own wallet `0xDEF`)

Communication: PostgreSQL-backed message queue.

## Commands

### Backend
```bash
cd backend
uv run pytest src/trustdesk/<module>/tests/   # test one module
uv run pytest --cov --cov-report=term-missing # test everything with coverage (must be 100%)
uv run ruff check src/                         # lint
uv run ruff format src/                        # format
uv run python scripts/run_desk.py              # start main desk
uv run python scripts/run_risk_manager.py      # start risk manager (separate terminal)
```

### Contracts
```bash
cd contracts
forge build    # compile
forge test     # test
```

### Dashboard
```bash
cd dashboard
npm run dev    # dev server
npm run build  # production build
npm run lint   # lint
```

### Infrastructure
```bash
docker compose up -d                           # start PostgreSQL
uv run python scripts/seed_db.py               # initialize DB
uv run python scripts/run_backtest.py          # run backtest
```

## Code Style

- Python: ruff, 120-char lines, type hints on all public functions
- TypeScript: strict mode, ESLint + Prettier
- snake_case (Python), camelCase (TypeScript)
- SCREAMING_SNAKE_CASE for constants
- Boolean functions: is_/has_ prefix
- Getters: get_ prefix
- Target 64% of files under 200 lines. Hook blocks files over 300 lines.

## Architecture Rules

- All external calls go through `adapters/`. Never import web3, anthropic, httpx, or subprocess in feature modules.
- Shared types live in `schemas/` (one file per schema). Module-internal types in the module's `types.py`.
- No direct imports between peer feature modules. Communicate through orchestrator graph or message queue.
- `schemas/` is the contract. If you change a schema, grep for all importers.
- Every module follows: `__init__.py` (public API), implementation files, `types.py`, `constants.py`, `tests/`.

## What NOT To Do

- Don't put business logic in adapters — they are thin wrappers.
- Don't use `os.environ` — use `core/config.py`.
- Don't create files over 300 lines — the hook will block you.
- Don't add dependencies without updating `pyproject.toml`.
- Don't skip type hints on public functions.
- Don't mock Kraken CLI in integration tests — use paper trading.
- Don't import between peer modules (e.g., `signal_engine` importing from `risk_manager`).
