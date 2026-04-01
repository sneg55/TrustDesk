"""Tests for Kraken subprocess runner."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.adapters.kraken.subprocess_runner import SubprocessRunner
from trustdesk.core.errors import KrakenError


def _make_process(stdout: str, returncode: int = 0) -> MagicMock:
    """Create a mock process with preset stdout/stderr."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
    return proc


def _make_error_process(stderr: str) -> MagicMock:
    """Create a mock process that fails."""
    proc = MagicMock()
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"", stderr.encode()))
    return proc


class TestSubprocessRunner:
    async def test_run_success(self) -> None:
        runner = SubprocessRunner()
        payload = {"result": {"XXBTZUSD": {"a": ["50100.0"]}}}
        proc = _make_process(json.dumps(payload))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
            result = await runner.run("ticker", ["--pair", "XXBTZUSD"])

        assert result == payload

    async def test_run_nonzero_exit(self) -> None:
        runner = SubprocessRunner()
        proc = _make_error_process("Error: invalid pair")

        mock = AsyncMock(return_value=proc)
        with (
            patch("asyncio.create_subprocess_exec", mock),
            pytest.raises(KrakenError, match="invalid pair"),
        ):
            await runner.run("ticker", ["--pair", "INVALID"])

    async def test_run_invalid_json(self) -> None:
        runner = SubprocessRunner()
        proc = _make_process("not json at all")

        mock = AsyncMock(return_value=proc)
        with (
            patch("asyncio.create_subprocess_exec", mock),
            pytest.raises(KrakenError, match="Invalid JSON"),
        ):
            await runner.run("ticker", [])

    async def test_run_passes_args_correctly(self) -> None:
        runner = SubprocessRunner()
        proc = _make_process("{}")

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)) as mock_exec:
            await runner.run("balance", [])

        mock_exec.assert_called_once_with(
            "kraken", "balance", "-o", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def test_run_with_extra_args(self) -> None:
        runner = SubprocessRunner()
        proc = _make_process("{}")

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)) as mock_exec:
            await runner.run("ticker", ["--pair", "XXBTZUSD"])

        mock_exec.assert_called_once_with(
            "kraken", "ticker", "--pair", "XXBTZUSD", "-o", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
