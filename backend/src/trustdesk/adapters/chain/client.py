"""Unified chain client for ERC-8004 on Base Sepolia."""
from __future__ import annotations

from typing import Any

from web3 import AsyncWeb3

from trustdesk.adapters.chain.gas_monitor import GasMonitor
from trustdesk.adapters.chain.identity import IdentityRegistry
from trustdesk.adapters.chain.reputation import ReputationRegistry
from trustdesk.adapters.chain.types import WritePriority
from trustdesk.adapters.chain.validation import ValidationRegistry
from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.logging import get_logger

log = get_logger(__name__)

# Minimal ABI stubs — full ABIs loaded from contract artifacts at deploy time
_MINIMAL_ABI: list[dict[str, Any]] = []


class ChainClient:
    """Unified interface for all on-chain operations."""

    def __init__(self, config: TrustDeskConfig) -> None:
        self._config = config
        self._w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(config.rpc_url))

        # Accounts
        self._agent_account = self._w3.eth.account.from_key(config.agent_private_key)
        self._validator_account = self._w3.eth.account.from_key(config.validator_private_key)

        # Gas monitor
        self._gas_monitor = GasMonitor(self._w3)

        # Registry contracts (ABI loaded externally; stubs for now)
        identity_contract = self._w3.eth.contract(
            address=config.trustdesk_identity_registry, abi=_MINIMAL_ABI,
        )
        reputation_contract = self._w3.eth.contract(
            address=config.trustdesk_reputation_registry, abi=_MINIMAL_ABI,
        )
        validation_contract = self._w3.eth.contract(
            address=config.trustdesk_validation_registry, abi=_MINIMAL_ABI,
        )

        self.identity = IdentityRegistry(identity_contract)
        self.reputation = ReputationRegistry(reputation_contract)
        self.validation = ValidationRegistry(validation_contract)

    @property
    def agent_address(self) -> str:
        return self._agent_account.address

    @property
    def validator_address(self) -> str:
        return self._validator_account.address

    @property
    def agent_tx_params(self) -> dict[str, str]:
        return {"from": self.agent_address}

    @property
    def validator_tx_params(self) -> dict[str, str]:
        return {"from": self.validator_address}

    async def check_agent_gas(self) -> tuple[float, WritePriority]:
        """Check gas balance for the agent wallet."""
        return await self._gas_monitor.check_balance(self.agent_address)

    async def check_validator_gas(self) -> tuple[float, WritePriority]:
        """Check gas balance for the validator wallet."""
        return await self._gas_monitor.check_balance(self.validator_address)

    async def should_write(self, role: str, priority: WritePriority) -> bool:
        """Check if a write should proceed for the given role and priority."""
        address = self.agent_address if role == "agent" else self.validator_address
        return await self._gas_monitor.should_write(address, priority)
