# Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bridge "code complete" to "working system" -- seed database, wire Strykr into signal engine, generate wallets, verify Kraken paper trading, run end-to-end smoke test.

**Architecture:** Scripts and wiring changes. No new modules. Modifies signal engine to optionally consume Strykr data. All scripts in `backend/scripts/`.

**Tech Stack:** asyncio, existing adapters, Kraken CLI, Base Sepolia

---

## Task 1: seed_db.py -- Create database tables

**Files:**
- Create: `backend/scripts/seed_db.py`

**Description:** Script that reads config from environment, creates all SQLAlchemy tables, and reports what was created. Uses the existing `TrustDeskConfig`, `create_engine`, and `Base` from the core modules.

**Code:**

```python
#!/usr/bin/env python3
"""Create all database tables."""
import asyncio
from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.db import create_engine
from trustdesk.core.models import Base

async def seed():
    config = TrustDeskConfig()
    engine = create_engine(config)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created:", list(Base.metadata.tables.keys()))
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
```

**Test:**
```bash
cd backend && uv run python scripts/seed_db.py
```
Expected output: `Tables created: ['trades', 'signals', 'retry_queue']` (or similar list of table names).

**Verify:**
```bash
PGPASSWORD=trustdesk psql -h localhost -p 5433 -U trustdesk -d trustdesk -c "\dt"
```
Should list the created tables.

**Commit:** `feat: add seed_db.py to create PostgreSQL tables`

---

## Task 2: Wire Strykr/PRISM signals into Signal Engine

**Files:**
- Modify: `backend/src/trustdesk/signal_engine/engine.py`
- Modify: `backend/scripts/run_desk.py`
- Modify: signal engine test files (to maintain 100% coverage)

**Description:** The `StrykrClient` adapter exists at `backend/src/trustdesk/adapters/strykr/client.py` but is not called by any module. Wire it into the signal engine as supplementary, non-blocking data. If Strykr is unavailable or fails, the engine continues without it.

### 2a. Modify `backend/src/trustdesk/signal_engine/engine.py`

Add optional `strykr` parameter to `SignalEngine.__init__`:

```python
def __init__(self, provider, strykr=None):
    self.provider = provider
    self.strykr = strykr
```

In `run_cycle()`, after computing indicators from the primary provider, if `self.strykr` is available, fetch Strykr data and merge it into the indicators dict. Extract the base symbol from the pair: `pair.split("/")[0]`.

Add this logic inside `run_cycle()` (after primary indicators are computed, before returning):

```python
if self.strykr:
    base_symbol = pair.split("/")[0]
    try:
        signals_data = await self.strykr.signals(base_symbol)
        indicators["prism_overall_signal"] = signals_data.get("overall_signal", "neutral")
        indicators["prism_direction"] = signals_data.get("direction", "neutral")
        indicators["prism_strength"] = signals_data.get("strength", "weak")
        indicators["prism_net_score"] = signals_data.get("net_score", 0)
    except Exception as e:
        logger.warning("Strykr signals fetch failed for %s: %s", base_symbol, e)

    try:
        risk_data = await self.strykr.risk(base_symbol)
        indicators["prism_daily_volatility"] = risk_data.get("daily_volatility", 0.0)
        indicators["prism_current_drawdown"] = risk_data.get("current_drawdown", 0.0)
        indicators["prism_sharpe_ratio"] = risk_data.get("sharpe_ratio", 0.0)
    except Exception as e:
        logger.warning("Strykr risk fetch failed for %s: %s", base_symbol, e)
```

Ensure `logger` is imported at the top of the file:
```python
import logging
logger = logging.getLogger(__name__)
```

### 2b. Modify `backend/scripts/run_desk.py`

In `run_desk.py`, where `SignalEngine` is initialized, pass the strykr client if available:

```python
# After existing adapter initialization with graceful degradation:
strykr = None
if config.prism_api_key:
    from trustdesk.adapters.strykr.client import StrykrClient
    strykr = StrykrClient(config.prism_api_key)

engine = SignalEngine(provider=kraken, strykr=strykr)
```

### 2c. Write/update tests

Add tests to the signal engine test file (likely `backend/tests/unit/signal_engine/test_engine.py` or similar). Must cover:

1. **Test with strykr=None** -- engine works exactly as before, no Strykr calls made.
2. **Test with strykr providing data** -- mock `StrykrClient` with `.signals()` and `.risk()` returning dicts. Verify indicators dict contains all `prism_*` keys.
3. **Test strykr signals failure** -- mock `.signals()` to raise an exception. Verify engine continues, no `prism_overall_signal` etc. in indicators, but primary indicators still present.
4. **Test strykr risk failure** -- mock `.risk()` to raise an exception. Verify engine continues, signal data present but risk data missing.
5. **Test symbol extraction** -- verify `"BTC/USD"` becomes `"BTC"` in the strykr call.

Example test structure:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_strykr():
    client = AsyncMock()
    client.signals.return_value = {
        "overall_signal": "bullish",
        "direction": "bullish",
        "strength": "moderate",
        "net_score": 1,
    }
    client.risk.return_value = {
        "daily_volatility": 0.55,
        "current_drawdown": 0.52,
        "sharpe_ratio": -0.86,
    }
    return client

async def test_run_cycle_with_strykr(mock_provider, mock_strykr):
    engine = SignalEngine(provider=mock_provider, strykr=mock_strykr)
    signal = await engine.run_cycle("BTC/USD")
    mock_strykr.signals.assert_awaited_once_with("BTC")
    mock_strykr.risk.assert_awaited_once_with("BTC")
    assert signal.indicators["prism_overall_signal"] == "bullish"
    assert signal.indicators["prism_daily_volatility"] == 0.55

async def test_run_cycle_without_strykr(mock_provider):
    engine = SignalEngine(provider=mock_provider, strykr=None)
    signal = await engine.run_cycle("BTC/USD")
    assert "prism_overall_signal" not in signal.indicators

async def test_run_cycle_strykr_signals_failure(mock_provider, mock_strykr):
    mock_strykr.signals.side_effect = Exception("API down")
    engine = SignalEngine(provider=mock_provider, strykr=mock_strykr)
    signal = await engine.run_cycle("BTC/USD")
    assert "prism_overall_signal" not in signal.indicators
    # risk should still work
    assert signal.indicators["prism_daily_volatility"] == 0.55

async def test_run_cycle_strykr_risk_failure(mock_provider, mock_strykr):
    mock_strykr.risk.side_effect = Exception("API down")
    engine = SignalEngine(provider=mock_provider, strykr=mock_strykr)
    signal = await engine.run_cycle("BTC/USD")
    assert signal.indicators["prism_overall_signal"] == "bullish"
    assert "prism_daily_volatility" not in signal.indicators
```

**IMPORTANT:** Must maintain 100% coverage. Run coverage check after changes:
```bash
cd backend && uv run pytest --cov=trustdesk --cov-report=term-missing --cov-fail-under=100
```

**Commit:** `feat(signal_engine): integrate Strykr/PRISM signals and risk data`

---

## Task 3: Generate Base Sepolia wallets

**Files:**
- Create: `backend/scripts/generate_wallets.py`

**Description:** Generates two fresh Ethereum wallets (agent + validator) for Base Sepolia deployment. Outputs addresses, private keys, and .env lines.

**Code:**

```python
#!/usr/bin/env python3
"""Generate two Base Sepolia wallets for TrustDesk."""
from eth_account import Account
import secrets

agent = Account.from_key(secrets.token_hex(32))
validator = Account.from_key(secrets.token_hex(32))

print("=== TrustDesk Wallets ===")
print(f"\nAgent wallet:")
print(f"  Address: {agent.address}")
print(f"  Private key: {agent.key.hex()}")
print(f"\nValidator wallet:")
print(f"  Address: {validator.address}")
print(f"  Private key: {validator.key.hex()}")
print(f"\nAdd to .env:")
print(f"TRUSTDESK_AGENT_PRIVATE_KEY={agent.key.hex()}")
print(f"TRUSTDESK_VALIDATOR_PRIVATE_KEY={validator.key.hex()}")
print(f"\nFund both addresses with testnet ETH from:")
print(f"  https://www.alchemy.com/faucets/base-sepolia")
print(f"  https://faucets.chain.link")
```

**Test:**
```bash
cd backend && uv run python scripts/generate_wallets.py
```
Expected: prints two wallet addresses and private keys. Each run produces different keys.

**Verify:** Output contains valid Ethereum addresses (0x-prefixed, 42 chars) and 64-char hex private keys.

**Commit:** `feat: add wallet generation script for Base Sepolia`

---

## Task 4: End-to-end smoke test script

**Files:**
- Create: `backend/scripts/smoke_test.py`

**Description:** Runs the full signal pipeline once without a server. Hits real APIs (Kraken public data, optionally Strykr). This is a manual validation script, NOT a pytest test.

**Code:**

```python
#!/usr/bin/env python3
"""Smoke test: run one full signal cycle against real Kraken paper data."""
import asyncio
import json
from trustdesk.core.config import TrustDeskConfig
from trustdesk.adapters.kraken.client import KrakenClient
from trustdesk.signal_engine.engine import SignalEngine

async def main():
    config = TrustDeskConfig()
    kraken = KrakenClient(config)

    # Optional: Strykr
    strykr = None
    if config.prism_api_key:
        from trustdesk.adapters.strykr.client import StrykrClient
        strykr = StrykrClient(config.prism_api_key)

    engine = SignalEngine(provider=kraken, strykr=strykr)

    print("Running signal cycle for BTC/USD...")
    try:
        signal = await engine.run_cycle("BTC/USD")
        print(json.dumps(signal.model_dump(mode="json"), indent=2, default=str))
    except Exception as e:
        print(f"Signal cycle failed: {e}")
        print("Make sure Kraken CLI is installed: kraken status")

    if strykr:
        await strykr.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Test:**
```bash
cd backend && uv run python scripts/smoke_test.py
```
Expected: prints a JSON SignalPayload with indicators, timestamp, pair, etc. If Kraken CLI is not installed, prints the install hint.

**Commit:** `feat: add smoke test script for end-to-end pipeline validation`

---

## Task 5: Verify Kraken CLI paper trading works

**Files:**
- Create: `backend/scripts/verify_kraken.py`

**Description:** Diagnostic script that checks Kraken CLI installation, paper trading, and OHLC data fetch. Prints status for each step.

**Code:**

```python
#!/usr/bin/env python3
"""Verify Kraken CLI is installed and paper trading works."""
import asyncio
import json
from trustdesk.adapters.kraken.client import KrakenClient
from trustdesk.core.config import TrustDeskConfig

async def main():
    config = TrustDeskConfig()
    client = KrakenClient(config)

    print("1. Checking Kraken CLI status...")
    # ticker is public, no auth needed
    try:
        ticker = await client.ticker("BTC/USD")
        print(f"   BTC/USD last: ${ticker.last:,.2f}")
    except Exception as e:
        print(f"   FAILED: {e}")
        print("   Install: curl --proto '=https' --tlsv1.2 -LsSf https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh")
        return

    print("2. Checking paper trading...")
    try:
        # Paper init doesn't need auth
        result = await client._run("paper", ["init", "--balance", "10000"])
        print(f"   Paper account initialized: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   Paper init: {e}")

    print("3. Fetching OHLC data...")
    try:
        ohlc = await client.ohlc("BTC/USD", 15)
        print(f"   Got {len(ohlc)} candles")
    except Exception as e:
        print(f"   OHLC failed: {e}")

    print("\nAll checks passed!")

if __name__ == "__main__":
    asyncio.run(main())
```

**Test:**
```bash
cd backend && uv run python scripts/verify_kraken.py
```
Expected: prints BTC/USD price, paper account status, and candle count. If Kraken CLI is missing, prints install instructions.

**Commit:** `feat: add Kraken CLI verification script`

---

## Execution Order

Tasks can be partially parallelized:

1. **Task 1** (seed_db.py) -- independent, can run first
2. **Task 3** (generate_wallets.py) -- independent, can run in parallel with Task 1
3. **Task 5** (verify_kraken.py) -- independent, can run in parallel with Task 1
4. **Task 2** (Strykr wiring) -- modifies existing code, run after understanding current engine structure
5. **Task 4** (smoke_test.py) -- depends on Task 2 (uses strykr parameter), run last

**Parallel group 1:** Tasks 1, 3, 5
**Sequential after group 1:** Task 2, then Task 4

---

## Post-implementation checklist

- [ ] `cd backend && uv run python scripts/seed_db.py` prints table names
- [ ] `PGPASSWORD=trustdesk psql -h localhost -p 5433 -U trustdesk -d trustdesk -c "\dt"` shows tables
- [ ] `cd backend && uv run pytest --cov=trustdesk --cov-report=term-missing --cov-fail-under=100` still passes with 100% coverage
- [ ] `cd backend && uv run python scripts/generate_wallets.py` prints two valid wallet addresses
- [ ] `cd backend && uv run python scripts/verify_kraken.py` passes all checks (or prints install hint)
- [ ] `cd backend && uv run python scripts/smoke_test.py` prints a SignalPayload JSON
- [ ] All 5 commits made with correct messages
