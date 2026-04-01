"""Main auditor pipeline: trust path, gas-aware writing, retry integration.

The auditor is called by the orchestrator AFTER trade execution.
It is deterministic desk infrastructure, NOT an LLM.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Protocol

from trustdesk.auditor.pass_logger import PassLogger
from trustdesk.auditor.reputation_lifecycle import (
    build_trade_close_feedback,
    build_trade_open_feedback,
    build_trade_update_feedback,
)
from trustdesk.auditor.retry import RetryManager
from trustdesk.auditor.types import ReputationEntry, TrustPathResult

logger = logging.getLogger(__name__)


class ChainAdapterProtocol(Protocol):
    """Minimal interface for the chain adapter."""

    gas_monitor: Any

    async def validation_request(self, cid: str) -> str: ...
    async def validation_response(self, cid: str) -> str: ...


class IpfsAdapterProtocol(Protocol):
    """Minimal interface for the IPFS adapter."""

    async def upload(self, data: bytes) -> str: ...


class Auditor:
    """Records every trade decision to ERC-8004 via IPFS + Chain.

    Trust path flow:
    1. Upload proposal to IPFS
    2. Call validationRequest() from agent wallet
    3. Upload verdict to IPFS
    4. Call validationResponse() from validator wallet
    """

    def __init__(
        self,
        *,
        chain_adapter: Any,
        ipfs_adapter: Any,
    ) -> None:
        self._chain = chain_adapter
        self._ipfs = ipfs_adapter
        self.pass_logger = PassLogger()
        self.retry_manager = RetryManager()

    async def post_reputation(
        self,
        entry: ReputationEntry,
    ) -> TrustPathResult:
        """Execute the trust path for a reputation entry."""
        # Gas check first
        if not self._chain.gas_monitor.is_gas_acceptable():
            logger.warning("Gas too high, skipping write for %s", entry.tag)
            return TrustPathResult(
                proposal_cid="",
                verdict_cid="",
                validation_request_tx="",
                validation_response_tx="",
                success=False,
                error="gas_too_high",
            )

        try:
            # Step 1: Upload proposal to IPFS
            proposal_data = json.dumps(
                {
                    "type": entry.feedback_type.value,
                    "score": entry.score,
                    "tag": entry.tag,
                    "skill": entry.skill,
                    "context": entry.context,
                },
            ).encode()
            proposal_cid = await self._ipfs.upload(proposal_data)

            # Step 2: validationRequest from agent wallet
            req_tx = await self._chain.validation_request(proposal_cid)

            # Step 3: Upload verdict to IPFS
            verdict_data = json.dumps(
                {
                    "proposal_cid": proposal_cid,
                    "score": entry.score,
                    "approved": True,
                },
            ).encode()
            verdict_cid = await self._ipfs.upload(verdict_data)

            # Step 4: validationResponse from validator wallet
            resp_tx = await self._chain.validation_response(verdict_cid)

        except Exception as exc:
            logger.error("Trust path failed: %s", exc)
            self.retry_manager.enqueue(
                task_id=str(uuid.uuid4()),
                payload={
                    "type": entry.feedback_type.value,
                    "score": entry.score,
                    "tag": entry.tag,
                    "skill": entry.skill,
                    "context": entry.context,
                },
            )
            return TrustPathResult(
                proposal_cid="",
                verdict_cid="",
                validation_request_tx="",
                validation_response_tx="",
                success=False,
                error=str(exc),
            )

        return TrustPathResult(
            proposal_cid=proposal_cid,
            verdict_cid=verdict_cid,
            validation_request_tx=req_tx,
            validation_response_tx=resp_tx,
            success=True,
        )

    async def record_trade_open(
        self,
        *,
        skill: str,
        entry_price: float,
        size_pct: float,
        regime: str,
        risk_verdict: str,
    ) -> TrustPathResult:
        """Stage 1: Record trade opened."""
        entry = build_trade_open_feedback(
            skill=skill,
            entry_price=entry_price,
            size_pct=size_pct,
            regime=regime,
            risk_verdict=risk_verdict,
        )
        return await self.post_reputation(entry)

    async def record_trade_update(
        self,
        *,
        skill: str,
        unrealized_pnl_pct: float,
        time_in_trade: str,
        stop_moved_to_breakeven: bool,
    ) -> TrustPathResult:
        """Stage 2: Record material change."""
        entry = build_trade_update_feedback(
            skill=skill,
            unrealized_pnl_pct=unrealized_pnl_pct,
            time_in_trade=time_in_trade,
            stop_moved_to_breakeven=stop_moved_to_breakeven,
        )
        return await self.post_reputation(entry)

    async def record_trade_close(
        self,
        *,
        skill: str,
        entry_price: float,
        exit_price: float,
        realized_pnl_pct: float,
        exit_reason: str,
    ) -> TrustPathResult:
        """Stage 3: Record trade closed."""
        entry = build_trade_close_feedback(
            skill=skill,
            entry_price=entry_price,
            exit_price=exit_price,
            realized_pnl_pct=realized_pnl_pct,
            exit_reason=exit_reason,
        )
        return await self.post_reputation(entry)
