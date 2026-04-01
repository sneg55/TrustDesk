"""Tests for chain identity registry adapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.adapters.chain.identity import IdentityRegistry
from trustdesk.core.errors import ChainError


def _mock_contract() -> MagicMock:
    """Create a mock web3 contract."""
    contract = MagicMock()
    contract.functions = MagicMock()
    return contract


class TestIdentityRegistryRegister:
    async def test_register_agent_success(self) -> None:
        contract = _mock_contract()
        tx_hash = b"\xab" * 32
        fn = MagicMock()
        fn.transact = AsyncMock(return_value=tx_hash)
        contract.functions.registerAgent = MagicMock(return_value=fn)

        registry = IdentityRegistry(contract)
        result = await registry.register_agent(
            address="0x" + "aa" * 20,
            metadata_uri="ipfs://QmTest",
            tx_params={"from": "0x" + "aa" * 20},
        )
        assert result == "0x" + "ab" * 32
        contract.functions.registerAgent.assert_called_once_with("0x" + "aa" * 20, "ipfs://QmTest")

    async def test_register_agent_failure(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.transact = AsyncMock(side_effect=Exception("revert"))
        contract.functions.registerAgent = MagicMock(return_value=fn)

        registry = IdentityRegistry(contract)
        with pytest.raises(ChainError, match="revert"):
            await registry.register_agent(
                address="0x" + "aa" * 20,
                metadata_uri="ipfs://QmTest",
                tx_params={"from": "0x" + "aa" * 20},
            )


class TestIdentityRegistryLookup:
    async def test_get_agent_metadata(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value="ipfs://QmMeta")
        contract.functions.getAgentMetadata = MagicMock(return_value=fn)

        registry = IdentityRegistry(contract)
        result = await registry.get_agent_metadata("0x" + "aa" * 20)
        assert result == "ipfs://QmMeta"

    async def test_is_registered_true(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value=True)
        contract.functions.isRegistered = MagicMock(return_value=fn)

        registry = IdentityRegistry(contract)
        assert await registry.is_registered("0x" + "aa" * 20) is True

    async def test_is_registered_false(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value=False)
        contract.functions.isRegistered = MagicMock(return_value=fn)

        registry = IdentityRegistry(contract)
        assert await registry.is_registered("0x" + "bb" * 20) is False
