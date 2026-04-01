"""IPFS adapter using Pinata for pin management."""
from __future__ import annotations

import json
from typing import Any

import httpx

from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.constants import ERROR_IDS
from trustdesk.core.errors import IPFSError
from trustdesk.core.logging import get_logger

log = get_logger(__name__)

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
PINATA_PIN_LIST_URL = "https://api.pinata.cloud/data/pinList"
PINATA_PIN_BY_HASH_URL = "https://api.pinata.cloud/pinning/pinByHash"


class IPFSClient:
    """Pinata-backed IPFS client for uploading and managing decision records."""

    def __init__(self, config: TrustDeskConfig) -> None:
        self._api_key = config.pinata_api_key
        self._api_secret = config.pinata_api_secret

    def _headers(self) -> dict[str, str]:
        return {
            "pinata_api_key": self._api_key,
            "pinata_secret_api_key": self._api_secret,
            "Content-Type": "application/json",
        }

    async def upload_json(self, data: dict[str, Any], name: str) -> str:
        """Upload a JSON object to IPFS via Pinata.

        Args:
            data: The JSON-serializable data to upload.
            name: A human-readable name for the pin.

        Returns:
            IPFS URI in the form ipfs://<CID>.

        Raises:
            IPFSError: On upload failure.
        """
        payload = {
            "pinataContent": data,
            "pinataMetadata": {"name": name},
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                PINATA_PIN_URL,
                headers=self._headers(),
                content=json.dumps(payload),
            )
            try:
                response.raise_for_status()
            except Exception as exc:
                raise IPFSError(
                    f"Pinata upload failed: {response.text}",
                    error_id=ERROR_IDS["IPFS_UPLOAD"],
                ) from exc

            result = response.json()
            cid = result["IpfsHash"]
            log.info("ipfs_uploaded", cid=cid, name=name)
            return f"ipfs://{cid}"

    async def verify_pin(self, cid: str) -> bool:
        """Check if a CID is currently pinned on Pinata.

        Args:
            cid: The IPFS content identifier to check.

        Returns:
            True if pinned, False otherwise.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                PINATA_PIN_LIST_URL,
                headers=self._headers(),
                params={"hashContains": cid, "status": "pinned"},
            )
            result = response.json()
            return len(result.get("rows", [])) > 0

    async def repin_if_needed(self, cids: list[str]) -> list[str]:
        """Check each CID and attempt to re-pin any that are missing.

        Args:
            cids: List of CIDs to verify and re-pin if needed.

        Returns:
            List of CIDs that failed to re-pin.
        """
        failed: list[str] = []
        async with httpx.AsyncClient() as client:
            for cid in cids:
                # Check if pinned
                check_resp = await client.get(
                    PINATA_PIN_LIST_URL,
                    headers=self._headers(),
                    params={"hashContains": cid, "status": "pinned"},
                )
                check_data = check_resp.json()
                if len(check_data.get("rows", [])) > 0:
                    continue

                # Attempt re-pin
                log.warning("ipfs_repin_needed", cid=cid)
                repin_resp = await client.post(
                    PINATA_PIN_BY_HASH_URL,
                    headers=self._headers(),
                    content=json.dumps({"hashToPin": cid}),
                )
                try:
                    repin_resp.raise_for_status()
                    log.info("ipfs_repinned", cid=cid)
                except Exception:
                    log.error("ipfs_repin_failed", cid=cid)
                    failed.append(cid)

        return failed
