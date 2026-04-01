"""Strykr/PRISM API client."""
from __future__ import annotations

import httpx

from trustdesk.adapters.strykr.types import PrismRisk, PrismSignal, ResolvedAsset
from trustdesk.core.logging import get_logger

log = get_logger(__name__)

_BASE_URL = "https://api.prismapi.ai"


class StrykrClient:
    """Async HTTP client for the Strykr/PRISM market intelligence API."""

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"X-API-Key": api_key},
            timeout=10.0,
        )

    async def resolve(self, symbol: str) -> ResolvedAsset:
        """Resolve canonical asset identity via /resolve/{symbol}.

        Args:
            symbol: Asset ticker, e.g. ``"BTC"``.

        Returns:
            Parsed :class:`ResolvedAsset` for the given symbol.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        response = await self._client.get(f"/resolve/{symbol}")
        response.raise_for_status()
        data = response.json()
        venues = data.get("venues", {}).get("data", [])
        log.info("strykr_resolve", symbol=symbol, confidence=data.get("confidence"))
        return ResolvedAsset(
            symbol=data["symbol"],
            name=data["name"],
            type=data["type"],
            confidence=data["confidence"],
            venues=venues,
        )

    async def signals(self, symbol: str) -> PrismSignal:
        """Fetch AI-powered market signals via /signals/{symbol}.

        Args:
            symbol: Asset ticker, e.g. ``"BTC"``.

        Returns:
            Parsed :class:`PrismSignal` for the given symbol.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        response = await self._client.get(f"/signals/{symbol}")
        response.raise_for_status()
        data = response.json()
        item = data["data"][0]
        log.info("strykr_signals", symbol=symbol, overall=item.get("overall_signal"))
        return PrismSignal.model_validate(item)

    async def risk(self, symbol: str) -> PrismRisk:
        """Fetch risk metrics via /risk/{symbol}.

        Args:
            symbol: Asset ticker, e.g. ``"BTC"``.

        Returns:
            Parsed :class:`PrismRisk` for the given symbol.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        response = await self._client.get(f"/risk/{symbol}")
        response.raise_for_status()
        data = response.json()
        log.info("strykr_risk", symbol=symbol, sharpe=data.get("sharpe_ratio"))
        return PrismRisk.model_validate(data)

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()
