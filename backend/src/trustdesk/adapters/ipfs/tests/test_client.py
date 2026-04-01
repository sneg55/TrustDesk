"""Tests for IPFSClient (Pinata)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trustdesk.adapters.ipfs.client import IPFSClient
from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.errors import IPFSError


def _config() -> TrustDeskConfig:
    return TrustDeskConfig(
        pinata_api_key="test-pinata-key",
        pinata_api_secret="test-pinata-secret",
        anthropic_api_key="test",
        trustdesk_agent_private_key="0x" + "ab" * 32,
        trustdesk_validator_private_key="0x" + "cd" * 32,
    )


def _mock_response(status: int, json_data: dict) -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


class TestIPFSClientUpload:
    async def test_upload_json_returns_uri(self) -> None:
        mock_http = AsyncMock()
        upload_resp = _mock_response(200, {
            "IpfsHash": "QmTestHash123",
            "PinSize": 1234,
            "Timestamp": "2026-01-01T00:00:00Z",
        })
        mock_http.post = AsyncMock(return_value=upload_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            result = await client.upload_json({"key": "value"}, "test-record")

        assert result == "ipfs://QmTestHash123"

    async def test_upload_json_failure_raises(self) -> None:
        mock_http = AsyncMock()
        error_resp = _mock_response(500, {"error": "Internal Server Error"})
        mock_http.post = AsyncMock(return_value=error_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            with pytest.raises(IPFSError):
                await client.upload_json({"key": "value"}, "test-record")


class TestIPFSClientVerify:
    async def test_verify_pin_success(self) -> None:
        mock_http = AsyncMock()
        pin_resp = _mock_response(200, {
            "rows": [{"ipfs_pin_hash": "QmTestHash123", "status": "pinned"}],
        })
        mock_http.get = AsyncMock(return_value=pin_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            result = await client.verify_pin("QmTestHash123")

        assert result is True

    async def test_verify_pin_not_found(self) -> None:
        mock_http = AsyncMock()
        pin_resp = _mock_response(200, {"rows": []})
        mock_http.get = AsyncMock(return_value=pin_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            result = await client.verify_pin("QmMissing")

        assert result is False


class TestIPFSClientRepin:
    async def test_repin_all_present(self) -> None:
        mock_http = AsyncMock()
        pin_resp = _mock_response(200, {
            "rows": [{"ipfs_pin_hash": "QmHash1"}, {"ipfs_pin_hash": "QmHash2"}],
        })
        mock_http.get = AsyncMock(return_value=pin_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            failed = await client.repin_if_needed(["QmHash1", "QmHash2"])

        assert failed == []

    async def test_repin_some_missing(self) -> None:
        mock_http = AsyncMock()
        # First call for QmHash1 - found
        pin_resp_1 = _mock_response(200, {
            "rows": [{"ipfs_pin_hash": "QmHash1"}],
        })
        # Second call for QmHash2 - not found
        pin_resp_2 = _mock_response(200, {"rows": []})
        # Third call - repin attempt for QmHash2 fails
        repin_resp = _mock_response(500, {"error": "failed"})
        mock_http.get = AsyncMock(side_effect=[pin_resp_1, pin_resp_2])
        mock_http.post = AsyncMock(return_value=repin_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            failed = await client.repin_if_needed(["QmHash1", "QmHash2"])

        assert failed == ["QmHash2"]

    async def test_repin_success(self) -> None:
        mock_http = AsyncMock()
        # Check - not found
        pin_resp = _mock_response(200, {"rows": []})
        # Repin - success
        repin_resp = _mock_response(200, {
            "IpfsHash": "QmHash1",
            "PinSize": 100,
            "Timestamp": "2026-01-01T00:00:00Z",
        })
        mock_http.get = AsyncMock(return_value=pin_resp)
        mock_http.post = AsyncMock(return_value=repin_resp)

        with patch("trustdesk.adapters.ipfs.client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            client = IPFSClient(_config())
            failed = await client.repin_if_needed(["QmHash1"])

        assert failed == []
