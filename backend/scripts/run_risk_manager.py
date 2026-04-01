#!/usr/bin/env python3
"""TrustDesk Risk Manager — separate process with validator wallet.

Listens for proposals on the message queue, evaluates them,
and publishes verdicts back.
"""

from __future__ import annotations

import asyncio
import logging

from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.logging import setup_logging
from trustdesk.core.queue import InMemoryQueue
from trustdesk.risk_manager.manager import RiskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trustdesk.risk_manager_process")


async def run() -> None:
    """Main loop: listen for proposals, evaluate, publish verdicts."""
    setup_logging()
    config = TrustDeskConfig()

    logger.info("Starting Risk Manager process (validator wallet)")
    logger.info("Mode: %s", config.mode)

    risk_manager = RiskManager()
    queue = InMemoryQueue()

    logger.info("Risk Manager ready, listening for proposals...")

    async for proposal in queue.subscribe("proposals"):
        logger.info("Received proposal: %s", proposal.get("proposal_id", "unknown"))
        try:
            verdict = await risk_manager.evaluate(proposal, tier="UNPROVEN")
            await queue.publish("verdicts", {
                "proposal_id": proposal.get("proposal_id"),
                "verdict": verdict,
            })
            logger.info("Published verdict for %s", proposal.get("proposal_id"))
        except Exception:
            logger.exception("Failed to evaluate proposal")


def main() -> None:
    """Entry point."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
