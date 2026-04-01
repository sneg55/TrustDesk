"""Reputation Registry adapter for ERC-8004."""
from __future__ import annotations

from typing import Any

from trustdesk.core.constants import ERROR_IDS
from trustdesk.core.errors import ChainError
from trustdesk.core.logging import get_logger

log = get_logger(__name__)


class ReputationRegistry:
    """Thin wrapper around the Reputation Registry smart contract."""

    def __init__(self, contract: Any) -> None:
        self._contract = contract

    async def give_feedback(
        self,
        agent_address: str,
        score: int,
        tag: str,
        skill: str,
        evidence_uri: str,
        tx_params: dict[str, Any],
    ) -> str:
        """Submit reputation feedback for an agent.

        Returns:
            Transaction hash as hex string.
        """
        try:
            tx_hash = await self._contract.functions.giveFeedback(
                agent_address, score, tag, skill, evidence_uri,
            ).transact(tx_params)
            log.info(
                "feedback_submitted",
                agent=agent_address,
                score=score,
                tag=tag,
                tx=tx_hash.hex(),
            )
            return "0x" + tx_hash.hex()
        except Exception as exc:
            raise ChainError(
                str(exc), error_id=ERROR_IDS["CHAIN_TX_FAILED"],
            ) from exc

    async def get_reputation_score(self, address: str) -> int:
        """Get the current reputation score for an agent."""
        return await self._contract.functions.getReputationScore(address).call()

    async def get_tier(self, address: str) -> int:
        """Get the current tier index for an agent."""
        return await self._contract.functions.getTier(address).call()
