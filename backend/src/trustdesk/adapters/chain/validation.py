"""Validation Registry adapter for ERC-8004."""
from __future__ import annotations

from typing import Any

from trustdesk.core.constants import ERROR_IDS
from trustdesk.core.errors import ChainError
from trustdesk.core.logging import get_logger

log = get_logger(__name__)


class ValidationRegistry:
    """Thin wrapper around the Validation Registry smart contract."""

    def __init__(self, contract: Any) -> None:
        self._contract = contract

    async def request_validation(
        self,
        proposal_id: str,
        evidence_uri: str,
        tx_params: dict[str, Any],
    ) -> str:
        """Submit a validation request for a proposal.

        Returns:
            Transaction hash as hex string.
        """
        try:
            tx_hash = await self._contract.functions.requestValidation(
                proposal_id, evidence_uri,
            ).transact(tx_params)
            log.info("validation_requested", proposal_id=proposal_id, tx=tx_hash.hex())
            return "0x" + tx_hash.hex()
        except Exception as exc:
            raise ChainError(
                str(exc), error_id=ERROR_IDS["CHAIN_TX_FAILED"],
            ) from exc

    async def respond_validation(
        self,
        proposal_id: str,
        approved: bool,
        evidence_uri: str,
        tx_params: dict[str, Any],
    ) -> str:
        """Respond to a validation request.

        Returns:
            Transaction hash as hex string.
        """
        try:
            tx_hash = await self._contract.functions.respondValidation(
                proposal_id, approved, evidence_uri,
            ).transact(tx_params)
            log.info(
                "validation_responded",
                proposal_id=proposal_id,
                approved=approved,
                tx=tx_hash.hex(),
            )
            return "0x" + tx_hash.hex()
        except Exception as exc:
            raise ChainError(
                str(exc), error_id=ERROR_IDS["CHAIN_TX_FAILED"],
            ) from exc

    async def get_validation_status(self, proposal_id: str) -> int:
        """Get the validation status for a proposal (enum index)."""
        return await self._contract.functions.getValidationStatus(proposal_id).call()

    async def get_validator(self, proposal_id: str) -> str:
        """Get the validator address assigned to a proposal."""
        return await self._contract.functions.getValidator(proposal_id).call()
