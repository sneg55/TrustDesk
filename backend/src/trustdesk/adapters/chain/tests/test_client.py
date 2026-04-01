"""Tests for ChainClient."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.adapters.chain.client import ChainClient
from trustdesk.adapters.chain.types import WritePriority
from trustdesk.core.config import TrustDeskConfig


def _config() -> TrustDeskConfig:
    return TrustDeskConfig(
        trustdesk_rpc_url="https://sepolia.base.org",
        trustdesk_agent_private_key="0x" + "ab" * 32,
        trustdesk_validator_private_key="0x" + "cd" * 32,
        trustdesk_identity_registry="0x" + "11" * 20,
        trustdesk_reputation_registry="0x" + "22" * 20,
        trustdesk_validation_registry="0x" + "33" * 20,
        anthropic_api_key="test",
    )


def _mock_w3() -> MagicMock:
    w3 = MagicMock()
    w3.eth = MagicMock()
    w3.eth.account = MagicMock()
    agent_acct = MagicMock()
    agent_acct.address = "0x" + "aa" * 20
    validator_acct = MagicMock()
    validator_acct.address = "0x" + "bb" * 20
    w3.eth.account.from_key = MagicMock(side_effect=[agent_acct, validator_acct])
    w3.eth.get_balance = AsyncMock(return_value=200_000_000_000_000_000)
    w3.from_wei = MagicMock(side_effect=lambda val, unit: val / 10**18)
    w3.eth.contract = MagicMock(return_value=MagicMock())
    return w3


class TestChainClientInit:
    def test_creates_accounts_from_keys(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        assert client.agent_address == "0x" + "aa" * 20
        assert client.validator_address == "0x" + "bb" * 20

    def test_agent_tx_params(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        params = client.agent_tx_params
        assert params["from"] == "0x" + "aa" * 20

    def test_validator_tx_params(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        params = client.validator_tx_params
        assert params["from"] == "0x" + "bb" * 20


class TestChainClientGas:
    async def test_check_agent_gas(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        balance, priority = await client.check_agent_gas()
        assert balance == pytest.approx(0.2)
        assert priority == WritePriority.NORMAL

    async def test_check_validator_gas(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        balance, priority = await client.check_validator_gas()
        assert balance == pytest.approx(0.2)
        assert priority == WritePriority.NORMAL

    async def test_should_write_agent(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        result = await client.should_write("agent", WritePriority.NORMAL)
        assert result is True

    async def test_should_write_validator(self) -> None:
        w3 = _mock_w3()
        with patch("trustdesk.adapters.chain.client.AsyncWeb3", return_value=w3):
            client = ChainClient(_config())
        result = await client.should_write("validator", WritePriority.NORMAL)
        assert result is True
