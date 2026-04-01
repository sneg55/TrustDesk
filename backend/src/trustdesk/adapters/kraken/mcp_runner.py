"""MCP-based Kraken runner (stub — subprocess is the reliable path)."""
from __future__ import annotations

from typing import Any

from trustdesk.core.logging import get_logger

log = get_logger(__name__)


class MCPRunner:
    """MCP client for Kraken. Currently a stub; subprocess is primary."""

    def is_available(self) -> bool:
        """Return whether MCP connection is active."""
        return False

    async def run(self, command: str, args: list[str]) -> dict[str, Any]:
        """Run a Kraken command via MCP.

        Raises:
            NotImplementedError: Always, until MCP integration is complete.
        """
        log.warning("mcp_not_implemented", command=command)
        raise NotImplementedError("MCP runner is not yet implemented")
