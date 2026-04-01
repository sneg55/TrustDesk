"""Tests for chain reputation registry adapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.adapters.chain.reputation import ReputationRegistry
from trustdesk.core.errors import ChainError


def _mock_contract() -> MagicMock:
    """Create a mock web3 contract."""
    contract = MagicMock()
    contract.functions = MagicMock()
    return contract


class TestReputationRegistryFeedback:
    async def test_give_feedback_success(self) -> None:
        contract = _mock_contract()
        tx_hash = b"\xcd" * 32
        fn = MagicMock()
        fn.transact = AsyncMock(return_value=tx_hash)
        contract.functions.giveFeedback = MagicMock(return_value=fn)

        registry = ReputationRegistry(contract)
        result = await registry.give_feedback(
            agent_address="0x" + "aa" * 20,
            score=85,
            tag="TRADE_CLOSED",
            skill="strategist",
            evidence_uri="ipfs://QmEvidence",
            tx_params={"from": "0x" + "bb" * 20},
        )
        assert result == "0x" + "cd" * 32

    async def test_give_feedback_failure(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.transact = AsyncMock(side_effect=Exception("gas too low"))
        contract.functions.giveFeedback = MagicMock(return_value=fn)

        registry = ReputationRegistry(contract)
        with pytest.raises(ChainError, match="gas too low"):
            await registry.give_feedback(
                agent_address="0x" + "aa" * 20,
                score=85,
                tag="TRADE_CLOSED",
                skill="strategist",
                evidence_uri="ipfs://QmEvidence",
                tx_params={"from": "0x" + "bb" * 20},
            )


class TestReputationRegistryQuery:
    async def test_get_reputation_score(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value=850)
        contract.functions.getReputationScore = MagicMock(return_value=fn)

        registry = ReputationRegistry(contract)
        result = await registry.get_reputation_score("0x" + "aa" * 20)
        assert result == 850

    async def test_get_tier(self) -> None:
        contract = _mock_contract()
        fn = MagicMock()
        fn.call = AsyncMock(return_value=2)
        contract.functions.getTier = MagicMock(return_value=fn)

        registry = ReputationRegistry(contract)
        result = await registry.get_tier("0x" + "aa" * 20)
        assert result == 2
