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
