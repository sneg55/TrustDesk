"""Tests for Kraken MCP runner (stub)."""
from __future__ import annotations

from trustdesk.adapters.kraken.mcp_runner import MCPRunner


class TestMCPRunner:
    def test_is_available_returns_false(self) -> None:
        runner = MCPRunner()
        assert runner.is_available() is False

    async def test_run_raises_not_implemented(self) -> None:
        import pytest

        runner = MCPRunner()
        with pytest.raises(NotImplementedError):
            await runner.run("ticker", ["--pair", "XXBTZUSD"])
