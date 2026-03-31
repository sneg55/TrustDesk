# Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the complete project foundation — Python package, Docker, config, schemas, DB, CLAUDE.md — so that all feature modules can be built independently on top of it.

**Architecture:** Monorepo with `backend/` (Python 3.11, uv), `contracts/` (Foundry), `dashboard/` (Vite + React). Backend is a single installable package `trustdesk` with co-located tests. PostgreSQL via Docker Compose. All shared types in `schemas/`, all config in `core/`.

**Tech Stack:** Python 3.11, uv, Pydantic, SQLAlchemy async, asyncpg, structlog, FastAPI, PostgreSQL 16, Alembic, ruff, pytest

**Subsequent plans** (can execute in parallel after this plan completes):
- Plan 2: Adapters (Kraken, Anthropic, Chain, IPFS)
- Plan 3: Signal Engine
- Plan 4: Reputation Engine + Risk Manager
- Plan 5: Strategist + Orchestrator
- Plan 6: Auditor + On-chain Integration
- Plan 7: API + Dashboard
- Plan 8: Contracts (Foundry)

---

### Task 1: Python Project Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/trustdesk/__init__.py`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `docker-compose.yml`

- [ ] **Step 1: Initialize uv project**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
mkdir -p backend/src/trustdesk
cd backend
uv init --name trustdesk --lib
```

- [ ] **Step 2: Replace pyproject.toml with full config**

Write `backend/pyproject.toml`:

```toml
[project]
name = "trustdesk"
version = "0.1.0"
description = "AI trading desk with reputation-gated capital access"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.4",
    "anthropic>=0.52",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "websockets>=14.0",
    "pandas>=2.2",
    "web3>=7.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "structlog>=24.4",
    "httpx>=0.28",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "pytest-cov>=6.0",
    "ruff>=0.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.backends"

[tool.hatch.build.targets.wheel]
packages = ["src/trustdesk"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["src"]
python_files = "test_*.py"
python_paths = ["src"]

[tool.coverage.run]
source = ["trustdesk"]
branch = true

[tool.coverage.report]
fail_under = 100
show_missing = true
exclude_also = [
    "if TYPE_CHECKING:",
    "pragma: no cover",
]

[tool.ruff]
target-version = "py311"
line-length = 120
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "TCH"]

[tool.ruff.lint.isort]
known-first-party = ["trustdesk"]
```

- [ ] **Step 3: Create package __init__.py**

Write `backend/src/trustdesk/__init__.py`:

```python
"""TrustDesk — AI trading desk with reputation-gated capital access."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Create .gitignore at repo root**

Write `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
*.egg

# uv
backend/uv.lock

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Claude
CLAUDE.local.md

# Database
pgdata/

# Node
node_modules/
dashboard/dist/

# Foundry
contracts/out/
contracts/cache/

# IPFS
*.pin

# Logs
*.log
```

- [ ] **Step 5: Create .env.example**

Write `.env.example`:

```bash
# Mode: "paper" (default) or "live"
TRUSTDESK_MODE=paper

# Kraken CLI (not needed for paper trading)
KRAKEN_API_KEY=
KRAKEN_API_SECRET=
TRUSTDESK_KRAKEN_MCP=true

# Anthropic (required)
ANTHROPIC_API_KEY=

# Base Sepolia (required for on-chain features)
TRUSTDESK_RPC_URL=https://sepolia.base.org
TRUSTDESK_AGENT_PRIVATE_KEY=
TRUSTDESK_VALIDATOR_PRIVATE_KEY=

# ERC-8004 Contract Addresses (filled after deployment)
TRUSTDESK_IDENTITY_REGISTRY=
TRUSTDESK_REPUTATION_REGISTRY=
TRUSTDESK_VALIDATION_REGISTRY=
TRUSTDESK_OPEN_VALIDATOR=

# IPFS / Pinata
PINATA_API_KEY=
PINATA_API_SECRET=

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://trustdesk:trustdesk@localhost:5432/trustdesk

# Tuning (optional)
TRUSTDESK_GAS_CHECK_INTERVAL=1800
TRUSTDESK_SIGNAL_INTERVAL=300
TRUSTDESK_LLM_MODEL=claude-sonnet-4-20250514
```

- [ ] **Step 6: Create docker-compose.yml**

Write `docker-compose.yml`:

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trustdesk"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 7: Install dependencies and verify**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv sync --all-extras
uv run python -c "import trustdesk; print(trustdesk.__version__)"
```

Expected: `0.1.0`

- [ ] **Step 8: Verify ruff and pytest work**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run ruff check src/
uv run pytest --co -q
uv run pytest --cov --cov-report=term-missing --co -q 2>&1 | head -5
```

Expected: ruff reports no issues, pytest collects 0 tests (none yet), coverage plugin loaded.

- [ ] **Step 9: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/pyproject.toml backend/src/trustdesk/__init__.py .gitignore .env.example docker-compose.yml
git commit -m "feat: initialize Python project with uv, Docker Compose, and config"
```

---

### Task 2: Core — Config

**Files:**
- Create: `backend/src/trustdesk/core/__init__.py`
- Create: `backend/src/trustdesk/core/config.py`
- Create: `backend/src/trustdesk/core/tests/__init__.py`
- Create: `backend/src/trustdesk/core/tests/test_config.py`

- [ ] **Step 1: Create core package**

```bash
mkdir -p backend/src/trustdesk/core/tests
```

Write `backend/src/trustdesk/core/__init__.py`:

```python
"""Core infrastructure: config, errors, logging, database, queue."""
```

Write `backend/src/trustdesk/core/tests/__init__.py`:

```python
```

- [ ] **Step 2: Write the failing test**

Write `backend/src/trustdesk/core/tests/test_config.py`:

```python
import os

import pytest

from trustdesk.core.config import TrustDeskConfig


def test_default_config_loads_paper_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config defaults to paper mode when TRUSTDESK_MODE is not set."""
    monkeypatch.delenv("TRUSTDESK_MODE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.mode == "paper"


def test_config_reads_mode_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config reads TRUSTDESK_MODE from environment."""
    monkeypatch.setenv("TRUSTDESK_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.mode == "live"


def test_config_optional_kraken_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kraken API keys are optional (paper trading needs none)."""
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.kraken_api_key is None
    assert config.kraken_api_secret is None


def test_config_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM model defaults to claude-sonnet-4-20250514."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.llm_model == "claude-sonnet-4-20250514"


def test_config_rpc_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """RPC URL defaults to Base Sepolia."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.rpc_url == "https://sepolia.base.org"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'trustdesk.core.config'`

- [ ] **Step 4: Write config implementation**

Write `backend/src/trustdesk/core/config.py`:

```python
"""Centralized configuration. Never use os.environ directly elsewhere."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class TrustDeskConfig(BaseSettings):
    """Single source of truth for all TrustDesk configuration."""

    model_config = {"env_prefix": "", "case_sensitive": False}

    # Mode
    trustdesk_mode: Literal["paper", "live"] = "paper"

    # Kraken
    kraken_api_key: str | None = None
    kraken_api_secret: str | None = None
    trustdesk_kraken_mcp: bool = True

    # Anthropic
    anthropic_api_key: str = ""

    # Chain (Base Sepolia)
    trustdesk_rpc_url: str = "https://sepolia.base.org"
    trustdesk_agent_private_key: str = ""
    trustdesk_validator_private_key: str = ""

    # ERC-8004 contract addresses
    trustdesk_identity_registry: str = ""
    trustdesk_reputation_registry: str = ""
    trustdesk_validation_registry: str = ""
    trustdesk_open_validator: str = ""

    # IPFS
    pinata_api_key: str = ""
    pinata_api_secret: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://trustdesk:trustdesk@localhost:5432/trustdesk"

    # Tuning
    trustdesk_gas_check_interval: int = 1800
    trustdesk_signal_interval: int = 300
    trustdesk_llm_model: str = "claude-sonnet-4-20250514"

    # Convenience properties that match the spec's naming
    @property
    def mode(self) -> str:
        return self.trustdesk_mode

    @property
    def rpc_url(self) -> str:
        return self.trustdesk_rpc_url

    @property
    def agent_private_key(self) -> str:
        return self.trustdesk_agent_private_key

    @property
    def validator_private_key(self) -> str:
        return self.trustdesk_validator_private_key

    @property
    def llm_model(self) -> str:
        return self.trustdesk_llm_model

    @property
    def kraken_mcp_enabled(self) -> bool:
        return self.trustdesk_kraken_mcp

    @property
    def gas_check_interval(self) -> int:
        return self.trustdesk_gas_check_interval

    @property
    def signal_interval(self) -> int:
        return self.trustdesk_signal_interval
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_config.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/core/
git commit -m "feat(core): add centralized config with pydantic-settings"
```

---

### Task 3: Core — Errors

**Files:**
- Create: `backend/src/trustdesk/core/errors.py`
- Create: `backend/src/trustdesk/core/tests/test_errors.py`

- [ ] **Step 1: Write the failing test**

Write `backend/src/trustdesk/core/tests/test_errors.py`:

```python
from trustdesk.core.errors import (
    ChainError,
    IPFSError,
    KrakenError,
    LLMUnavailableError,
    RiskCheckFailed,
    TrustDeskError,
    ValidationError,
    error_message,
    to_error,
)


def test_error_hierarchy() -> None:
    """All custom errors inherit from TrustDeskError."""
    assert issubclass(KrakenError, TrustDeskError)
    assert issubclass(ChainError, TrustDeskError)
    assert issubclass(LLMUnavailableError, TrustDeskError)
    assert issubclass(IPFSError, TrustDeskError)
    assert issubclass(ValidationError, TrustDeskError)
    assert issubclass(RiskCheckFailed, TrustDeskError)


def test_error_message_from_exception() -> None:
    """error_message extracts string from any exception."""
    assert error_message(ValueError("bad input")) == "bad input"


def test_error_message_from_string() -> None:
    """error_message handles strings directly."""
    assert error_message("raw error") == "raw error"


def test_error_message_from_unknown() -> None:
    """error_message converts unknown types to string."""
    assert error_message(42) == "42"


def test_to_error_wraps_non_trustdesk_exception() -> None:
    """to_error wraps non-TrustDeskError in TrustDeskError."""
    original = ValueError("bad")
    wrapped = to_error(original)
    assert isinstance(wrapped, TrustDeskError)
    assert wrapped.__cause__ is original


def test_to_error_passes_through_trustdesk_error() -> None:
    """to_error returns TrustDeskError subclasses unchanged."""
    original = KrakenError("connection failed")
    result = to_error(original)
    assert result is original


def test_error_has_error_id() -> None:
    """Errors carry an error_id for tracking."""
    err = KrakenError("fail", error_id=1001)
    assert err.error_id == 1001
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_errors.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write errors implementation**

Write `backend/src/trustdesk/core/errors.py`:

```python
"""Error hierarchy and safe extraction helpers."""

from __future__ import annotations


class TrustDeskError(Exception):
    """Base error for all TrustDesk exceptions."""

    def __init__(self, message: str = "", *, error_id: int = 0) -> None:
        super().__init__(message)
        self.error_id = error_id


class KrakenError(TrustDeskError):
    """Kraken CLI communication failure."""


class ChainError(TrustDeskError):
    """Blockchain / web3 interaction failure."""


class LLMUnavailableError(TrustDeskError):
    """Anthropic API unreachable or rate-limited."""


class IPFSError(TrustDeskError):
    """IPFS / Pinata upload failure."""


class ValidationError(TrustDeskError):
    """Schema or input validation failure."""


class RiskCheckFailed(TrustDeskError):
    """Hard limit breach — trade must be rejected."""


def error_message(exc: object) -> str:
    """Safely extract a human-readable message from any value."""
    if isinstance(exc, Exception):
        return str(exc)
    return str(exc)


def to_error(exc: Exception) -> TrustDeskError:
    """Wrap any exception as a TrustDeskError, or pass through if already one."""
    if isinstance(exc, TrustDeskError):
        return exc
    wrapped = TrustDeskError(str(exc))
    wrapped.__cause__ = exc
    return wrapped
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_errors.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/core/errors.py backend/src/trustdesk/core/tests/test_errors.py
git commit -m "feat(core): add error hierarchy with safe extraction helpers"
```

---

### Task 4: Core — Constants

**Files:**
- Create: `backend/src/trustdesk/core/constants.py`
- Create: `backend/src/trustdesk/core/tests/test_constants.py`

- [ ] **Step 1: Write the failing test**

Write `backend/src/trustdesk/core/tests/test_constants.py`:

```python
from trustdesk.core.constants import (
    ERROR_IDS,
    REGIMES,
    SUPPORTED_PAIRS,
    TIERS,
    VERDICTS,
)


def test_supported_pairs() -> None:
    """Three pairs supported per spec."""
    assert SUPPORTED_PAIRS == ("BTC/USD", "ETH/USD", "SOL/USD")


def test_regimes() -> None:
    """Four market regimes."""
    assert set(REGIMES) == {"TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"}


def test_tiers() -> None:
    """Three reputation tiers."""
    assert set(TIERS) == {"UNPROVEN", "ESTABLISHED", "TRUSTED"}


def test_verdicts() -> None:
    """Four verdict types."""
    expected = {"APPROVED", "APPROVED_WITH_MODIFICATION", "APPROVED_HARD_ONLY", "REJECTED"}
    assert set(VERDICTS) == expected


def test_error_ids_are_unique() -> None:
    """All error IDs are distinct integers."""
    values = list(ERROR_IDS.values())
    assert len(values) == len(set(values))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_constants.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write constants implementation**

Write `backend/src/trustdesk/core/constants.py`:

```python
"""Global constants. Domain-specific constants live in their module's constants.py."""

# Supported trading pairs
SUPPORTED_PAIRS: tuple[str, ...] = ("BTC/USD", "ETH/USD", "SOL/USD")

# Market regimes
REGIMES: tuple[str, ...] = ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE")

# Reputation tiers
TIERS: tuple[str, ...] = ("UNPROVEN", "ESTABLISHED", "TRUSTED")

# Risk verdict types
VERDICTS: tuple[str, ...] = (
    "APPROVED",
    "APPROVED_WITH_MODIFICATION",
    "APPROVED_HARD_ONLY",
    "REJECTED",
)

# Alignment grades
ALIGNMENT_GRADES: tuple[str, ...] = ("STRONG", "MODERATE", "WEAK", "NO_SIGNAL")

# Error IDs — sequential, add new ones at the end
# Next ID: 1007
ERROR_IDS: dict[str, int] = {
    "KRAKEN_CONNECTION": 1001,
    "KRAKEN_COMMAND": 1002,
    "CHAIN_RPC": 1003,
    "CHAIN_TX_FAILED": 1004,
    "LLM_UNAVAILABLE": 1005,
    "IPFS_UPLOAD": 1006,
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_constants.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/core/constants.py backend/src/trustdesk/core/tests/test_constants.py
git commit -m "feat(core): add global constants for pairs, regimes, tiers, verdicts"
```

---

### Task 5: Core — Structured Logging

**Files:**
- Create: `backend/src/trustdesk/core/logging.py`
- Create: `backend/src/trustdesk/core/tests/test_logging.py`

- [ ] **Step 1: Write the failing test**

Write `backend/src/trustdesk/core/tests/test_logging.py`:

```python
import structlog

from trustdesk.core.logging import get_logger, setup_logging


def test_get_logger_returns_bound_logger() -> None:
    """get_logger returns a structlog BoundLogger with module name."""
    setup_logging()
    logger = get_logger("risk_manager")
    assert isinstance(logger, structlog.stdlib.BoundLogger)


def test_logger_binds_module_name() -> None:
    """Logger has module name bound by default."""
    setup_logging()
    logger = get_logger("signal_engine")
    # Access the bound values through the internal context
    ctx = structlog.get_context(logger)
    assert ctx["module"] == "signal_engine"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_logging.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write logging implementation**

Write `backend/src/trustdesk/core/logging.py`:

```python
"""Structured logging with correlation IDs."""

from __future__ import annotations

import structlog


def setup_logging(json_output: bool = False) -> None:
    """Configure structlog. Call once at startup."""
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(module: str) -> structlog.stdlib.BoundLogger:
    """Get a logger with the module name pre-bound."""
    return structlog.get_logger(module=module)


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the current context (async-safe via contextvars)."""
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    structlog.contextvars.unbind_contextvars("correlation_id")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_logging.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/core/logging.py backend/src/trustdesk/core/tests/test_logging.py
git commit -m "feat(core): add structured logging with correlation ID support"
```

---

### Task 6: Schemas — Shared Pydantic Models

**Files:**
- Create: `backend/src/trustdesk/schemas/__init__.py`
- Create: `backend/src/trustdesk/schemas/proposal.py`
- Create: `backend/src/trustdesk/schemas/verdict.py`
- Create: `backend/src/trustdesk/schemas/signal_payload.py`
- Create: `backend/src/trustdesk/schemas/reputation.py`
- Create: `backend/src/trustdesk/schemas/callbacks.py`
- Create: `backend/src/trustdesk/schemas/tests/__init__.py`
- Create: `backend/src/trustdesk/schemas/tests/test_proposal.py`
- Create: `backend/src/trustdesk/schemas/tests/test_verdict.py`
- Create: `backend/src/trustdesk/schemas/tests/test_signal_payload.py`
- Create: `backend/src/trustdesk/schemas/tests/test_reputation.py`

- [ ] **Step 1: Create schemas package**

```bash
mkdir -p backend/src/trustdesk/schemas/tests
```

Write `backend/src/trustdesk/schemas/__init__.py`:

```python
"""Shared Pydantic models — the contract between all modules."""

from trustdesk.schemas.callbacks import PositionCallback
from trustdesk.schemas.proposal import TradeProposal
from trustdesk.schemas.reputation import ReputationFeedback, TierDefinition
from trustdesk.schemas.signal_payload import Alignment, AlignmentBreakdown, DerivedValues, SignalPayload
from trustdesk.schemas.verdict import FieldModification, RiskVerdict

__all__ = [
    "Alignment",
    "AlignmentBreakdown",
    "DerivedValues",
    "FieldModification",
    "PositionCallback",
    "ReputationFeedback",
    "RiskVerdict",
    "SignalPayload",
    "TierDefinition",
    "TradeProposal",
]
```

Write `backend/src/trustdesk/schemas/tests/__init__.py`:

```python
```

- [ ] **Step 2: Write TradeProposal test**

Write `backend/src/trustdesk/schemas/tests/test_proposal.py`:

```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from trustdesk.schemas.proposal import TradeProposal


def _valid_proposal(**overrides: object) -> dict:
    """Factory for a valid TradeProposal dict."""
    base = {
        "agent_id": "agent_001",
        "proposal_id": "prop_20260401_001",
        "timestamp": datetime(2026, 4, 1, 14, 32, tzinfo=timezone.utc),
        "action": "BUY",
        "pair": "BTC/USD",
        "size_pct": 8.0,
        "entry_price_limit": 68200.00,
        "entry_type": "LIMIT",
        "stop_loss": 67519.25,
        "take_profit_1": 69010.00,
        "take_profit_2": 69870.00,
        "time_horizon": "4h",
        "reasoning": "Trend confirmed with ADX above 25.",
        "invalidation": "Close if regime shifts to TRENDING_DOWN.",
    }
    base.update(overrides)
    return base


def test_valid_proposal_creates_successfully() -> None:
    """A proposal with all required fields validates."""
    proposal = TradeProposal(**_valid_proposal())
    assert proposal.pair == "BTC/USD"
    assert proposal.action == "BUY"


def test_optional_fields_default_to_none() -> None:
    """Optional enrichment fields default to None."""
    proposal = TradeProposal(**_valid_proposal())
    assert proposal.alignment_score is None
    assert proposal.alignment_grade is None
    assert proposal.override_justification is None
    assert proposal.signals_cited is None


def test_proposal_with_alignment_enrichment() -> None:
    """Proposal accepts optional signal alignment data."""
    proposal = TradeProposal(
        **_valid_proposal(
            alignment_score=0.80,
            alignment_grade="MODERATE",
            regime_at_proposal="TRENDING_UP",
            signals_cited=["ema_crossover: BULLISH"],
        )
    )
    assert proposal.alignment_score == 0.80
    assert proposal.alignment_grade == "MODERATE"


def test_invalid_action_rejected() -> None:
    """Action must be BUY or SELL."""
    with pytest.raises(ValidationError):
        TradeProposal(**_valid_proposal(action="SHORT"))


def test_proposal_serializes_to_dict() -> None:
    """Proposal can round-trip through dict."""
    data = _valid_proposal()
    proposal = TradeProposal(**data)
    dumped = proposal.model_dump()
    assert dumped["pair"] == "BTC/USD"
    assert dumped["size_pct"] == 8.0
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/schemas/tests/test_proposal.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write TradeProposal schema**

Write `backend/src/trustdesk/schemas/proposal.py`:

```python
"""TradeProposal — submitted by any agent through the Agent Interface."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TradeProposal(BaseModel):
    """A trade proposal submitted by an agent to the desk."""

    agent_id: str
    proposal_id: str
    timestamp: datetime
    action: Literal["BUY", "SELL"]
    pair: str
    size_pct: float
    entry_price_limit: float
    entry_type: Literal["LIMIT"] = "LIMIT"
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None = None
    time_horizon: str
    reasoning: str
    invalidation: str

    # Optional enrichment from signal-aware agents
    alignment_score: float | None = None
    alignment_grade: Literal["STRONG", "MODERATE", "WEAK", "NO_SIGNAL"] | None = None
    override_justification: str | None = None
    regime_at_proposal: Literal["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"] | None = None
    signals_cited: list[str] | None = None
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/schemas/tests/test_proposal.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Write RiskVerdict test**

Write `backend/src/trustdesk/schemas/tests/test_verdict.py`:

```python
from trustdesk.schemas.verdict import FieldModification, RiskVerdict


def _valid_verdict(**overrides: object) -> dict:
    base = {
        "proposal_id": "prop_001",
        "validator_address": "0xDEF123",
        "verdict": "APPROVED",
        "tier_at_verdict": "UNPROVEN",
        "modifications": None,
        "hard_checks": {
            "position_size": "PASS (3% < 3%)",
            "total_exposure": "PASS (3% < 40%)",
            "daily_loss": "PASS (0% < 3%)",
            "max_positions": "PASS (0/1)",
            "cooldown": "PASS (no recent trades)",
        },
        "soft_checks": {"correlation": "PASS"},
        "reasoning": "All checks passed.",
    }
    base.update(overrides)
    return base


def test_approved_verdict() -> None:
    verdict = RiskVerdict(**_valid_verdict())
    assert verdict.verdict == "APPROVED"
    assert verdict.evidence_uri is None


def test_verdict_with_modification() -> None:
    mods = {
        "size_pct": FieldModification(original=8.0, approved=5.5, reason="Correlated exposure"),
    }
    verdict = RiskVerdict(**_valid_verdict(verdict="APPROVED_WITH_MODIFICATION", modifications=mods))
    assert verdict.modifications["size_pct"].approved == 5.5


def test_hard_only_verdict() -> None:
    verdict = RiskVerdict(
        **_valid_verdict(
            verdict="APPROVED_HARD_ONLY",
            soft_checks="SKIPPED_LLM_UNAVAILABLE",
        )
    )
    assert verdict.soft_checks == "SKIPPED_LLM_UNAVAILABLE"


def test_verdict_serializes() -> None:
    verdict = RiskVerdict(**_valid_verdict())
    dumped = verdict.model_dump()
    assert dumped["validator_address"] == "0xDEF123"
```

- [ ] **Step 7: Write RiskVerdict schema**

Write `backend/src/trustdesk/schemas/verdict.py`:

```python
"""RiskVerdict — returned by the Risk Manager after evaluating a proposal."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FieldModification(BaseModel):
    """A single field that was modified by the Risk Manager."""

    original: float
    approved: float
    reason: str


class RiskVerdict(BaseModel):
    """The Risk Manager's verdict on a trade proposal."""

    proposal_id: str
    validator_address: str
    verdict: Literal["APPROVED", "APPROVED_WITH_MODIFICATION", "APPROVED_HARD_ONLY", "REJECTED"]
    tier_at_verdict: Literal["UNPROVEN", "ESTABLISHED", "TRUSTED"]
    modifications: dict[str, FieldModification] | None = None
    hard_checks: dict[str, str]
    soft_checks: dict[str, str] | Literal["SKIPPED_LLM_UNAVAILABLE"]
    reasoning: str
    evidence_uri: str | None = None
    on_chain_tx: str | None = None
```

- [ ] **Step 8: Write SignalPayload test**

Write `backend/src/trustdesk/schemas/tests/test_signal_payload.py`:

```python
from datetime import datetime, timezone

from trustdesk.schemas.signal_payload import (
    Alignment,
    AlignmentBreakdown,
    DerivedValues,
    SignalPayload,
)


def _valid_payload(**overrides: object) -> dict:
    base = {
        "timestamp": datetime(2026, 4, 1, 14, 30, tzinfo=timezone.utc),
        "pair": "BTC/USD",
        "price": 68150.20,
        "regime": "TRENDING_UP",
        "regime_confidence": 0.82,
        "regime_changed": False,
        "signals": {
            "ema_crossover": "BULLISH",
            "adx": 31.4,
            "rsi_1h": 52.3,
            "volume_multiplier": 1.85,
        },
        "alignment": Alignment(
            score=0.80,
            grade="MODERATE",
            signals_agreeing=4,
            signals_total=5,
            breakdown=AlignmentBreakdown(
                ema_direction=True,
                adx_strength=True,
                volume_confirmation=True,
                obv_trend_match=True,
                book_imbalance_favorable=False,
            ),
        ),
        "derived": DerivedValues(
            suggested_stop_distance=630.75,
            position_size_pct=8.0,
            regime_aligned=True,
        ),
    }
    base.update(overrides)
    return base


def test_valid_signal_payload() -> None:
    payload = SignalPayload(**_valid_payload())
    assert payload.regime == "TRENDING_UP"
    assert payload.alignment.score == 0.80
    assert payload.alignment.breakdown.ema_direction is True


def test_alignment_grade_matches_score() -> None:
    payload = SignalPayload(**_valid_payload())
    assert payload.alignment.grade == "MODERATE"
    assert payload.alignment.signals_agreeing == 4


def test_derived_values() -> None:
    payload = SignalPayload(**_valid_payload())
    assert payload.derived.suggested_stop_distance == 630.75
    assert payload.derived.regime_aligned is True


def test_payload_serializes() -> None:
    payload = SignalPayload(**_valid_payload())
    dumped = payload.model_dump()
    assert dumped["price"] == 68150.20
    assert dumped["alignment"]["score"] == 0.80
```

- [ ] **Step 9: Write SignalPayload schema**

Write `backend/src/trustdesk/schemas/signal_payload.py`:

```python
"""SignalPayload — output of the Signal Engine, input to the Strategist."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AlignmentBreakdown(BaseModel):
    """Which of the 5 directional signals agree with the proposed direction."""

    ema_direction: bool
    adx_strength: bool
    volume_confirmation: bool
    obv_trend_match: bool
    book_imbalance_favorable: bool


class Alignment(BaseModel):
    """Signal Alignment Score — deterministic, computed by Signal Engine."""

    score: float
    grade: Literal["STRONG", "MODERATE", "WEAK", "NO_SIGNAL"]
    signals_agreeing: int
    signals_total: int = 5
    breakdown: AlignmentBreakdown


class DerivedValues(BaseModel):
    """Pre-computed trading parameters from Signal Engine."""

    suggested_stop_distance: float
    position_size_pct: float
    regime_aligned: bool


class SignalPayload(BaseModel):
    """Complete signal payload emitted every cycle by the Signal Engine."""

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

- [ ] **Step 10: Write reputation and callbacks schemas**

Write `backend/src/trustdesk/schemas/reputation.py`:

```python
"""Reputation types — feedback entries and tier definitions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ReputationFeedback(BaseModel):
    """A single feedback entry posted to ERC-8004 Reputation Registry."""

    type: Literal["TRADE_OPENED", "TRADE_UPDATE", "TRADE_CLOSED", "PASS_SUMMARY", "RISK_ADJUST"]
    score: int
    tag: str
    skill: str
    evidence_uri: str
    context: dict[str, Any]


class TierDefinition(BaseModel):
    """Capital and risk limits for a reputation tier."""

    tier: Literal["UNPROVEN", "ESTABLISHED", "TRUSTED"]
    capital_allocation: float
    max_position_pct: float
    max_open_trades: int
    max_daily_loss_pct: float
```

Write `backend/src/trustdesk/schemas/callbacks.py`:

```python
"""Position lifecycle callbacks — sent from desk to connected agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class PositionCallback(BaseModel):
    """Notification sent to an agent about a position lifecycle event."""

    event: Literal["FILLED", "PARTIAL_EXIT", "STOP_TRIGGERED", "TIME_EXIT", "INVALIDATION_EXIT", "DEMOTION"]
    proposal_id: str
    timestamp: datetime
    details: dict[str, Any]
```

- [ ] **Step 11: Write reputation test**

Write `backend/src/trustdesk/schemas/tests/test_reputation.py`:

```python
from trustdesk.schemas.reputation import ReputationFeedback, TierDefinition


def test_trade_opened_feedback() -> None:
    feedback = ReputationFeedback(
        type="TRADE_OPENED",
        score=50,
        tag="trade_open",
        skill="BTC/USD",
        evidence_uri="ipfs://bafybeig.../decision_001.json",
        context={"entry_price": 68200.00, "size_pct": 5.5},
    )
    assert feedback.score == 50
    assert feedback.tag == "trade_open"


def test_trade_closed_feedback_with_pnl() -> None:
    feedback = ReputationFeedback(
        type="TRADE_CLOSED",
        score=78,
        tag="trade_close",
        skill="BTC/USD",
        evidence_uri="ipfs://bafybeig.../close.json",
        context={"realized_pnl_pct": 1.19, "exit_reason": "TP1_HIT"},
    )
    assert feedback.score == 78


def test_unproven_tier() -> None:
    tier = TierDefinition(
        tier="UNPROVEN",
        capital_allocation=100.0,
        max_position_pct=3.0,
        max_open_trades=1,
        max_daily_loss_pct=3.0,
    )
    assert tier.capital_allocation == 100.0
    assert tier.max_open_trades == 1


def test_trusted_tier() -> None:
    tier = TierDefinition(
        tier="TRUSTED",
        capital_allocation=1000.0,
        max_position_pct=10.0,
        max_open_trades=5,
        max_daily_loss_pct=5.0,
    )
    assert tier.max_position_pct == 10.0
```

- [ ] **Step 12: Run all schema tests**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/schemas/tests/ -v
```

Expected: All 17 tests PASS.

- [ ] **Step 13: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/schemas/
git commit -m "feat(schemas): add all shared Pydantic models — proposal, verdict, signal, reputation, callbacks"
```

---

### Task 7: Core — Database Models & Setup

**Files:**
- Create: `backend/src/trustdesk/core/db.py`
- Create: `backend/src/trustdesk/core/models.py`
- Create: `backend/src/trustdesk/core/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Write `backend/src/trustdesk/core/tests/test_models.py`:

```python
from sqlalchemy import inspect

from trustdesk.core.models import Base, RetryQueue, Signal, Trade


def test_trade_table_name() -> None:
    assert Trade.__tablename__ == "trades"


def test_signal_table_name() -> None:
    assert Signal.__tablename__ == "signals"


def test_retry_queue_table_name() -> None:
    assert RetryQueue.__tablename__ == "retry_queue"


def test_trade_columns_exist() -> None:
    mapper = inspect(Trade)
    col_names = {c.key for c in mapper.column_attrs}
    required = {"id", "proposal_id", "agent_id", "pair", "action", "status", "created_at"}
    assert required.issubset(col_names)


def test_all_models_share_base() -> None:
    """All models use the same declarative base for Alembic."""
    tables = Base.metadata.tables
    assert "trades" in tables
    assert "signals" in tables
    assert "retry_queue" in tables
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write models implementation**

Write `backend/src/trustdesk/core/models.py`:

```python
"""SQLAlchemy models for PostgreSQL persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


class Trade(Base):
    """Trade lifecycle — from proposal through execution to outcome."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    pair: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(4))  # BUY or SELL
    size_pct: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit_1: Mapped[float] = mapped_column(Float)
    take_profit_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="proposed")  # proposed/approved/executed/closed
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tier_at_trade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    proposal_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verdict_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_uri: Mapped[str | None] = mapped_column(String(256), nullable=True)
    on_chain_tx: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Signal(Base):
    """Signal Engine output history — for backtest replay."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(16), index=True)
    regime: Mapped[str] = mapped_column(String(16))
    alignment_score: Mapped[float] = mapped_column(Float)
    alignment_grade: Mapped[str] = mapped_column(String(16))
    payload_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RetryQueue(Base):
    """Failed on-chain writes pending retry."""

    __tablename__ = "retry_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation: Mapped[str] = mapped_column(String(64))  # e.g. "give_feedback", "validation_response"
    payload_json: Mapped[dict] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Write db.py (connection factory)**

Write `backend/src/trustdesk/core/db.py`:

```python
"""PostgreSQL connection and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trustdesk.core.config import TrustDeskConfig


def create_engine(config: TrustDeskConfig):
    """Create an async SQLAlchemy engine from config."""
    return create_async_engine(config.database_url, echo=False)


def create_session_factory(config: TrustDeskConfig) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    engine = create_engine(config)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_models.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/core/models.py backend/src/trustdesk/core/db.py backend/src/trustdesk/core/tests/test_models.py
git commit -m "feat(core): add SQLAlchemy models for trades, signals, retry queue"
```

---

### Task 8: Core — Message Queue

**Files:**
- Create: `backend/src/trustdesk/core/queue.py`
- Create: `backend/src/trustdesk/core/tests/test_queue.py`

- [ ] **Step 1: Write the failing test**

Write `backend/src/trustdesk/core/tests/test_queue.py`:

```python
import asyncio
import json

import pytest

from trustdesk.core.queue import InMemoryQueue


@pytest.fixture
def queue() -> InMemoryQueue:
    return InMemoryQueue()


async def test_publish_and_receive(queue: InMemoryQueue) -> None:
    """Published message is received by subscriber."""
    received: list[dict] = []

    async def consume():
        async for msg in queue.subscribe("proposals"):
            received.append(msg)
            break  # Stop after first message

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await queue.publish("proposals", {"proposal_id": "prop_001"})
    await asyncio.wait_for(task, timeout=1.0)
    assert received == [{"proposal_id": "prop_001"}]


async def test_separate_channels(queue: InMemoryQueue) -> None:
    """Messages on different channels don't cross."""
    received: list[dict] = []

    async def consume():
        async for msg in queue.subscribe("verdicts"):
            received.append(msg)
            break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await queue.publish("proposals", {"wrong": "channel"})
    await queue.publish("verdicts", {"verdict": "APPROVED"})
    await asyncio.wait_for(task, timeout=1.0)
    assert received == [{"verdict": "APPROVED"}]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_queue.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write queue implementation**

Write `backend/src/trustdesk/core/queue.py`:

```python
"""Internal message queue for inter-process communication.

InMemoryQueue for single-process dev/testing.
PostgreSQL-backed queue for production (desk + risk_manager as separate processes).
"""

from __future__ import annotations

import asyncio
import json
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest src/trustdesk/core/tests/test_queue.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/core/queue.py backend/src/trustdesk/core/tests/test_queue.py
git commit -m "feat(core): add async message queue with in-memory implementation"
```

---

### Task 9: CLAUDE.md Hierarchy & Rules

**Files:**
- Create: `CLAUDE.md`
- Create: `CLAUDE.local.md`
- Create: `.claude/rules/testing.md`
- Create: `.claude/rules/git-workflow.md`
- Create: `.claude/rules/code-style.md`
- Create: `.claude/rules/security.md`

- [ ] **Step 1: Write CLAUDE.md**

Write `CLAUDE.md`:

```markdown
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
```

- [ ] **Step 2: Write CLAUDE.local.md**

Write `CLAUDE.local.md`:

```markdown
# Local Preferences

<!-- Personal overrides go here. This file is gitignored. -->
```

- [ ] **Step 3: Write .claude/rules/testing.md**

Write `.claude/rules/testing.md`:

```markdown
# Testing Rules

## Structure
- Co-located: each module has `tests/` inside it
- Run one module: `uv run pytest src/trustdesk/<module>/tests/ -v`
- Run all with coverage: `uv run pytest --cov --cov-report=term-missing`
- Coverage target: **100%**. `fail_under = 100` in pyproject.toml — CI will fail if coverage drops.

## By Module Type
- signal_engine, reputation, hard_checks: pure unit tests, no mocks needed
- strategist, soft_checks: mock AnthropicClient, test prompt construction + response parsing
- adapters/kraken: integration tests using `kraken paper` commands
- adapters/chain: test against Base Sepolia testnet
- orchestrator: integration tests with full graph execution
- api: TestClient from FastAPI

## Patterns
- Use pytest fixtures in each module's conftest.py
- Use factory functions (e.g., `_valid_proposal()`) for test data
- asyncio_mode = "auto" — no need for @pytest.mark.asyncio
- Test behavior, not implementation. Assert outputs, not internal calls.
```

- [ ] **Step 4: Write .claude/rules/git-workflow.md**

Write `.claude/rules/git-workflow.md`:

```markdown
# Git Workflow

- Branch naming: `feature/<module>-<description>`, `fix/<module>-<description>`
- Commits: imperative mood, "why not what", prefix with `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- Include module scope: `feat(signal_engine): add regime detection`
- One logical change per commit
- PR into main, squash merge
```

- [ ] **Step 5: Write .claude/rules/code-style.md**

Write `.claude/rules/code-style.md`:

```markdown
# Code Style

## Python
- ruff for linting and formatting
- Line length: 120
- Type hints on all public functions and methods
- `from __future__ import annotations` in every file
- Imports: stdlib → third-party → local, enforced by ruff isort

## Naming
- Files: snake_case always
- Classes: PascalCase
- Functions/methods: snake_case
- Constants: SCREAMING_SNAKE_CASE
- Booleans: is_/has_ prefix
- Private: single underscore prefix

## File Size
- Target: under 200 lines
- Warning: 200-300 lines (hook warns)
- Blocked: over 300 lines (hook blocks write)
- Split by concern: types.py, constants.py, separate implementation files

## Patterns
- No magic strings — use constants
- No raw os.environ — use core/config.py
- Comments explain WHY, never WHAT
- Use `from __future__ import annotations` for forward refs
```

- [ ] **Step 6: Write .claude/rules/security.md**

Write `.claude/rules/security.md`:

```markdown
# Security

- Never commit .env, private keys, or API secrets
- All secrets via environment variables through core/config.py
- Validator wallet key MUST be separate from agent wallet key
- Kraken API key permissions: minimum required per use case
- IPFS evidence is public — never include private keys or raw API responses with secrets
- Use --validate flag on Kraken orders during development
- Paper trading by default (TRUSTDESK_MODE=paper)
```

- [ ] **Step 7: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add CLAUDE.md CLAUDE.local.md .claude/rules/
git commit -m "docs: add CLAUDE.md hierarchy and .claude/rules for AI-driven development"
```

---

### Task 10: Module Directory Scaffolding

**Files:**
- Create empty `__init__.py` and `tests/__init__.py` for all feature modules

This creates the skeleton so agents can start working on any module independently.

- [ ] **Step 1: Create all module directories and __init__.py files**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend/src/trustdesk

# Feature modules
for mod in orchestrator signal_engine strategist risk_manager auditor reputation; do
  mkdir -p $mod/tests
  echo '"""'$mod' module."""' > $mod/__init__.py
  touch $mod/tests/__init__.py
  touch $mod/types.py
  touch $mod/constants.py
done

# Adapters
for adapter in kraken anthropic chain ipfs; do
  mkdir -p adapters/$adapter/tests
  touch adapters/$adapter/__init__.py
  touch adapters/$adapter/tests/__init__.py
done
echo '"""External service adapters."""' > adapters/__init__.py

# API
mkdir -p api/routes api/tests
echo '"""FastAPI application."""' > api/__init__.py
touch api/tests/__init__.py
```

- [ ] **Step 2: Verify structure**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
find src/trustdesk -name "__init__.py" | sort
```

Expected: `__init__.py` in every module, adapter, tests directory.

- [ ] **Step 3: Verify all modules are importable**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run python -c "
import trustdesk.orchestrator
import trustdesk.signal_engine
import trustdesk.strategist
import trustdesk.risk_manager
import trustdesk.auditor
import trustdesk.reputation
import trustdesk.schemas
import trustdesk.core
import trustdesk.adapters
print('All modules importable')
"
```

Expected: `All modules importable`

- [ ] **Step 4: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add backend/src/trustdesk/
git commit -m "feat: scaffold all module directories with __init__.py and tests"
```

---

### Task 11: Dashboard & Contracts Scaffold

**Files:**
- Create: `dashboard/package.json`, `dashboard/vite.config.ts`, `dashboard/tsconfig.json`, `dashboard/tailwind.config.ts`, `dashboard/src/main.tsx`, `dashboard/src/App.tsx`, `dashboard/index.html`
- Create: `contracts/foundry.toml`

- [ ] **Step 1: Scaffold dashboard with Vite**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
npm create vite@latest dashboard -- --template react-ts
```

- [ ] **Step 2: Install dashboard dependencies**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/dashboard
npm install
npm install viem recharts
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Tailwind**

Replace `dashboard/vite.config.ts`:

```typescript
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

Add to the top of `dashboard/src/index.css`:

```css
@import "tailwindcss";
```

- [ ] **Step 4: Replace App.tsx with placeholder**

Write `dashboard/src/App.tsx`:

```tsx
function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <header className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">TrustDesk</h1>
        <span className="px-3 py-1 bg-yellow-600 text-black text-sm font-mono rounded">
          PAPER
        </span>
      </header>
      <main className="text-gray-400">
        <p>Dashboard loading...</p>
      </main>
    </div>
  );
}

export default App;
```

- [ ] **Step 5: Verify dashboard builds**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/dashboard
npm run build
```

Expected: Build succeeds, output in `dist/`.

- [ ] **Step 6: Scaffold Foundry project**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
forge init contracts --no-commit --no-git
```

- [ ] **Step 7: Verify Foundry builds**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/contracts
forge build
```

Expected: Build succeeds.

- [ ] **Step 8: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add dashboard/ contracts/
git commit -m "feat: scaffold dashboard (Vite+React+Tailwind) and contracts (Foundry)"
```

---

### Task 12: README & Final Verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Write `README.md`:

```markdown
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
cd backend && uv run pytest -v                 # all tests
cd backend && uv run pytest src/trustdesk/<module>/tests/ -v  # one module
cd contracts && forge test                     # contract tests
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
```

- [ ] **Step 2: Run full test suite with coverage**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk/backend
uv run pytest --cov --cov-report=term-missing -v
uv run ruff check src/
```

Expected: All tests pass, 100% coverage, no lint issues.

- [ ] **Step 3: Commit**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk
git add README.md
git commit -m "docs: add README with quick start, architecture overview"
```

- [ ] **Step 4: Final verification — everything runs**

```bash
cd /Users/sneg55/Documents/GitHub/TrustDesk

# Python package
cd backend && uv run python -c "import trustdesk; print(f'trustdesk v{trustdesk.__version__}')" && cd ..

# Tests + 100% coverage
cd backend && uv run pytest --cov --cov-report=term-missing --tb=short && cd ..

# Lint
cd backend && uv run ruff check src/ && cd ..

# Dashboard
cd dashboard && npm run build && cd ..

# Contracts
cd contracts && forge build && cd ..

echo "Foundation complete."
```

Expected: All commands succeed. Foundation is ready for feature module development.
