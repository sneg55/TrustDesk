"""Tests for the main auditor pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trustdesk.auditor.auditor import Auditor
from trustdesk.auditor.types import FeedbackStage, ReputationEntry


@pytest.fixture()
def mock_chain_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.gas_monitor = MagicMock()
    adapter.gas_monitor.is_gas_acceptable = MagicMock(return_value=True)
    adapter.validation_request = AsyncMock(return_value="0xtxhash_req")
    adapter.validation_response = AsyncMock(return_value="0xtxhash_resp")
    adapter.post_reputation = AsyncMock(return_value="0xtxhash_rep")
    return adapter


@pytest.fixture()
def mock_ipfs_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.upload = AsyncMock(return_value="QmTestCid123")
    return adapter


@pytest.fixture()
def auditor(
    mock_chain_adapter: MagicMock,
    mock_ipfs_adapter: MagicMock,
) -> Auditor:
    return Auditor(
        chain_adapter=mock_chain_adapter,
        ipfs_adapter=mock_ipfs_adapter,
    )


class TestAuditorTrustPath:
    """Trust path: IPFS upload + on-chain write."""

    @pytest.mark.asyncio()
    async def test_post_reputation_uploads_to_ipfs_first(
        self,
        auditor: Auditor,
        mock_ipfs_adapter: MagicMock,
    ) -> None:
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_OPENED,
            score=50,
            tag="trade_open",
            skill="BTC/USD",
            evidence_uri="",
            context={"entry_price": 68200},
        )
        result = await auditor.post_reputation(entry)
        assert mock_ipfs_adapter.upload.called
        assert result.proposal_cid == "QmTestCid123"

    @pytest.mark.asyncio()
    async def test_post_reputation_calls_chain_validation(
        self,
        auditor: Auditor,
        mock_chain_adapter: MagicMock,
    ) -> None:
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_OPENED,
            score=50,
            tag="trade_open",
            skill="BTC/USD",
            evidence_uri="",
            context={"entry_price": 68200},
        )
        result = await auditor.post_reputation(entry)
        assert mock_chain_adapter.validation_request.called
        assert mock_chain_adapter.validation_response.called
        assert result.success is True

    @pytest.mark.asyncio()
    async def test_post_reputation_returns_tx_hashes(
        self,
        auditor: Auditor,
    ) -> None:
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_OPENED,
            score=50,
            tag="trade_open",
            skill="BTC/USD",
            evidence_uri="",
            context={},
        )
        result = await auditor.post_reputation(entry)
        assert result.validation_request_tx == "0xtxhash_req"
        assert result.validation_response_tx == "0xtxhash_resp"


class TestAuditorGasAwareness:
    """Gas-aware writing: skip low-priority writes when gas is high."""

    @pytest.mark.asyncio()
    async def test_skips_write_when_gas_unacceptable(
        self,
        auditor: Auditor,
        mock_chain_adapter: MagicMock,
    ) -> None:
        mock_chain_adapter.gas_monitor.is_gas_acceptable.return_value = False
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_UPDATE,
            score=60,
            tag="trade_update",
            skill="BTC/USD",
            evidence_uri="",
            context={},
        )
        result = await auditor.post_reputation(entry)
        assert result.success is False
        assert result.error == "gas_too_high"
        assert not mock_chain_adapter.validation_request.called

    @pytest.mark.asyncio()
    async def test_proceeds_when_gas_acceptable(
        self,
        auditor: Auditor,
        mock_chain_adapter: MagicMock,
    ) -> None:
        mock_chain_adapter.gas_monitor.is_gas_acceptable.return_value = True
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_OPENED,
            score=50,
            tag="trade_open",
            skill="BTC/USD",
            evidence_uri="",
            context={},
        )
        result = await auditor.post_reputation(entry)
        assert result.success is True


class TestAuditorRetryIntegration:
    """Failed writes go to retry queue."""

    @pytest.mark.asyncio()
    async def test_failed_chain_write_enqueued_for_retry(
        self,
        auditor: Auditor,
        mock_chain_adapter: MagicMock,
    ) -> None:
        mock_chain_adapter.validation_request.side_effect = Exception("RPC down")
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_OPENED,
            score=50,
            tag="trade_open",
            skill="BTC/USD",
            evidence_uri="",
            context={},
        )
        result = await auditor.post_reputation(entry)
        assert result.success is False
        assert auditor.retry_manager.queue_length == 1

    @pytest.mark.asyncio()
    async def test_failed_ipfs_upload_enqueued_for_retry(
        self,
        auditor: Auditor,
        mock_ipfs_adapter: MagicMock,
    ) -> None:
        mock_ipfs_adapter.upload.side_effect = Exception("Pinata timeout")
        entry = ReputationEntry(
            feedback_type=FeedbackStage.TRADE_OPENED,
            score=50,
            tag="trade_open",
            skill="BTC/USD",
            evidence_uri="",
            context={},
        )
        result = await auditor.post_reputation(entry)
        assert result.success is False
        assert auditor.retry_manager.queue_length == 1


class TestAuditorTradeLifecycle:
    """Full lifecycle: open -> update -> close."""

    @pytest.mark.asyncio()
    async def test_record_trade_open(self, auditor: Auditor) -> None:
        result = await auditor.record_trade_open(
            skill="BTC/USD",
            entry_price=68200.0,
            size_pct=5.5,
            regime="TRENDING_UP",
            risk_verdict="APPROVED",
        )
        assert result.success is True

    @pytest.mark.asyncio()
    async def test_record_trade_update(self, auditor: Auditor) -> None:
        result = await auditor.record_trade_update(
            skill="BTC/USD",
            unrealized_pnl_pct=1.2,
            time_in_trade="2h15m",
            stop_moved_to_breakeven=True,
        )
        assert result.success is True

    @pytest.mark.asyncio()
    async def test_record_trade_close(self, auditor: Auditor) -> None:
        result = await auditor.record_trade_close(
            skill="BTC/USD",
            entry_price=68200.0,
            exit_price=69010.0,
            realized_pnl_pct=1.19,
            exit_reason="TP1_HIT",
        )
        assert result.success is True
