"""Subprocess-based Kraken CLI runner."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from trustdesk.core.constants import ERROR_IDS
from trustdesk.core.errors import KrakenError
from trustdesk.core.logging import get_logger

log = get_logger(__name__)


class SubprocessRunner:
    """Execute Kraken CLI commands via subprocess and return parsed JSON."""

    async def run(self, command: str, args: list[str]) -> dict[str, Any]:
        """Run a kraken CLI command and return parsed JSON output.

        Args:
            command: The kraken subcommand (e.g. "ticker", "balance").
            args: Additional arguments (e.g. ["--pair", "XXBTZUSD"]).

        Returns:
            Parsed JSON dict from stdout.

        Raises:
            KrakenError: On non-zero exit or invalid JSON.
        """
        full_args = ["kraken", command, *args, "-o", "json"]
        log.debug("kraken_subprocess", command=command, args=args)

        proc = await asyncio.create_subprocess_exec(
            *full_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            msg = stderr.decode().strip()
            log.error("kraken_subprocess_error", command=command, stderr=msg)
            raise KrakenError(msg, error_id=ERROR_IDS["KRAKEN_COMMAND"])

        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            raise KrakenError(
                f"Invalid JSON from kraken {command}",
                error_id=ERROR_IDS["KRAKEN_COMMAND"],
            ) from exc
