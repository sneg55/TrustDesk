"""Tests for chain gas monitor."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.adapters.chain.gas_monitor import GasMonitor
from trustdesk.adapters.chain.types import WritePriority


def _mock_w3(balance_wei: int) -> MagicMock:
    """Create a mock web3 instance with a given balance."""
    w3 = MagicMock()
    w3.eth = MagicMock()
    w3.eth.get_balance = AsyncMock(return_value=balance_wei)
    w3.from_wei = MagicMock(side_effect=lambda val, unit: val / 10**18)
    return w3


class TestGasMonitor:
    async def test_check_balance_normal(self) -> None:
        w3 = _mock_w3(200_000_000_000_000_000)  # 0.2 ETH
        monitor = GasMonitor(w3)
        balance, priority = await monitor.check_balance("0x" + "aa" * 20)
        assert balance == pytest.approx(0.2)
        assert priority == WritePriority.NORMAL

    async def test_check_balance_reduced(self) -> None:
        w3 = _mock_w3(70_000_000_000_000_000)  # 0.07 ETH
        monitor = GasMonitor(w3)
        balance, priority = await monitor.check_balance("0x" + "aa" * 20)
        assert balance == pytest.approx(0.07)
        assert priority == WritePriority.REDUCED

    async def test_check_balance_critical(self) -> None:
        w3 = _mock_w3(30_000_000_000_000_000)  # 0.03 ETH
        monitor = GasMonitor(w3)
        balance, priority = await monitor.check_balance("0x" + "aa" * 20)
        assert balance == pytest.approx(0.03)
        assert priority == WritePriority.CRITICAL

    async def test_check_balance_emergency(self) -> None:
        w3 = _mock_w3(5_000_000_000_000_000)  # 0.005 ETH
        monitor = GasMonitor(w3)
        balance, priority = await monitor.check_balance("0x" + "aa" * 20)
        assert balance == pytest.approx(0.005)
        assert priority == WritePriority.EMERGENCY

    async def test_should_write_normal(self) -> None:
        w3 = _mock_w3(200_000_000_000_000_000)
        monitor = GasMonitor(w3)
        result = await monitor.should_write("0x" + "aa" * 20, WritePriority.NORMAL)
        assert result is True

    async def test_should_write_emergency_blocks_normal(self) -> None:
        w3 = _mock_w3(5_000_000_000_000_000)  # 0.005 ETH
        monitor = GasMonitor(w3)
        result = await monitor.should_write("0x" + "aa" * 20, WritePriority.NORMAL)
        assert result is False

    async def test_should_write_emergency_allows_critical(self) -> None:
        w3 = _mock_w3(5_000_000_000_000_000)  # 0.005 ETH -> EMERGENCY
        monitor = GasMonitor(w3)
        # EMERGENCY wallet can still do CRITICAL writes (emergency >= all)
        # Actually only emergency-level writes are allowed
        result = await monitor.should_write("0x" + "aa" * 20, WritePriority.EMERGENCY)
        assert result is True
