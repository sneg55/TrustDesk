"""Identity Registry adapter for ERC-8004."""
from __future__ import annotations

from typing import Any

from trustdesk.core.constants import ERROR_IDS
from trustdesk.core.errors import ChainError
from trustdesk.core.logging import get_logger

log = get_logger(__name__)


class IdentityRegistry:
    """Thin wrapper around the Identity Registry smart contract."""

    def __init__(self, contract: Any) -> None:
        self._contract = contract

    async def register_agent(
        self, address: str, metadata_uri: str, tx_params: dict[str, Any],
    ) -> str:
        """Register an agent on-chain.

        Returns:
            Transaction hash as hex string.
        """
        try:
            tx_hash = await self._contract.functions.registerAgent(
                address, metadata_uri,
            ).transact(tx_params)
            log.info("agent_registered", address=address, tx=tx_hash.hex())
            return "0x" + tx_hash.hex()
        except Exception as exc:
            raise ChainError(
                str(exc), error_id=ERROR_IDS["CHAIN_TX_FAILED"],
            ) from exc

    async def get_agent_metadata(self, address: str) -> str:
        """Get the metadata URI for a registered agent."""
        return await self._contract.functions.getAgentMetadata(address).call()

    async def is_registered(self, address: str) -> bool:
        """Check if an address is registered as an agent."""
        return await self._contract.functions.isRegistered(address).call()
