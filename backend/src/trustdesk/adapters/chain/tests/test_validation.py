"""Tests for chain validation registry adapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.adapters.chain.validation import ValidationRegistry
from trustdesk.core.errors import ChainError


def _mock_contract() -> MagicMock:
    """Create a mock web3 contract."""
    contract = MagicMock()
    contract.functions = MagicMock()
    return contract


class TestValidationRegistryRequest:
    async def test_request_validation_success(self) -> None:
        contract = _mock_contract()
        tx_hash = b"\xef" * 32
        fn = MagicMock()
        fn.transact = AsyncMock(return_value=tx_hash)
        contract.functions.requestValidation = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        result = await registry.request_validation(
            proposal_id="prop-1",
            evidence_uri="ipfs://QmProposal",
            tx_params={"from": "0x" + "aa" * 20},
        )
        assert result == "0x" + "ef" * 32

    async def test_request_validation_failure(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.transact = AsyncMock(side_effect=Exception("nonce too low"))
        contract.functions.requestValidation = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        with pytest.raises(ChainError, match="nonce too low"):
            await registry.request_validation(
                proposal_id="prop-1",
                evidence_uri="ipfs://QmProposal",
                tx_params={"from": "0x" + "aa" * 20},
            )


class TestValidationRegistryRespond:
    async def test_respond_validation_success(self) -> None:
        contract = _mock_contract()
        tx_hash = b"\x12" * 32
        fn = MagicMock()
        fn.transact = AsyncMock(return_value=tx_hash)
        contract.functions.respondValidation = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        result = await registry.respond_validation(
            proposal_id="prop-1",
            approved=True,
            evidence_uri="ipfs://QmVerdict",
            tx_params={"from": "0x" + "bb" * 20},
        )
        assert result == "0x" + "12" * 32

    async def test_respond_validation_rejected(self) -> None:
        contract = _mock_contract()
        tx_hash = b"\x34" * 32
        fn = MagicMock()
        fn.transact = AsyncMock(return_value=tx_hash)
        contract.functions.respondValidation = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        result = await registry.respond_validation(
            proposal_id="prop-1",
            approved=False,
            evidence_uri="ipfs://QmRejected",
            tx_params={"from": "0x" + "bb" * 20},
        )
        assert result == "0x" + "34" * 32
        contract.functions.respondValidation.assert_called_once_with(
            "prop-1", False, "ipfs://QmRejected",
        )


class TestValidationRegistryRespondFailure:
    async def test_respond_validation_failure(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.transact = AsyncMock(side_effect=Exception("insufficient gas"))
        contract.functions.respondValidation = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        with pytest.raises(ChainError, match="insufficient gas"):
            await registry.respond_validation(
                proposal_id="prop-1",
                approved=True,
                evidence_uri="ipfs://QmVerdict",
                tx_params={"from": "0x" + "bb" * 20},
            )


class TestValidationRegistryQuery:
    async def test_get_validation_status(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value=1)  # 1 = APPROVED
        contract.functions.getValidationStatus = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        result = await registry.get_validation_status("prop-1")
        assert result == 1

    async def test_get_validator_for_proposal(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value="0x" + "cc" * 20)
        contract.functions.getValidator = MagicMock(return_value=fn)

        registry = ValidationRegistry(contract)
        result = await registry.get_validator("prop-1")
        assert result == "0x" + "cc" * 20
