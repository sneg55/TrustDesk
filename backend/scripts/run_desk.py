#!/usr/bin/env python3
"""TrustDesk main desk process.

Starts: Signal Engine, Strategist, Orchestrator, Auditor, FastAPI server.
Run the Risk Manager separately via run_risk_manager.py.
"""

from __future__ import annotations

import logging

import uvicorn

from trustdesk.adapters.kraken.client import KrakenClient
from trustdesk.api.app import create_app
from trustdesk.api.events import EventBus
from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.logging import setup_logging
from trustdesk.orchestrator.graph import build_graph
from trustdesk.reputation.engine import ReputationEngine
from trustdesk.risk_manager.circuit_breaker import CircuitBreaker
from trustdesk.risk_manager.manager import RiskManager
from trustdesk.schemas.signal_payload import SignalPayload
from trustdesk.signal_engine.engine import SignalEngine
from trustdesk.strategist.strategist import Strategist

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trustdesk.desk")


def _try_chain(config: TrustDeskConfig):
    """Try to initialize ChainClient; return None if keys not configured."""
    if not config.agent_private_key:
        logger.warning("TRUSTDESK_AGENT_PRIVATE_KEY not set — chain disabled")
        return None
    from trustdesk.adapters.chain.client import ChainClient
    return ChainClient(config)


def _try_ipfs(config: TrustDeskConfig):
    """Try to initialize IPFSClient; return None if keys not configured."""
    if not config.pinata_api_key:
        logger.warning("PINATA_API_KEY not set — IPFS disabled")
        return None
    from trustdesk.adapters.ipfs.client import IPFSClient
    return IPFSClient(config)


def _try_anthropic(config: TrustDeskConfig):
    """Try to initialize AnthropicClient; return None if key not configured."""
    if not config.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — LLM disabled")
        return None
    from trustdesk.adapters.anthropic.client import AnthropicClient
    return AnthropicClient(config)


def _try_strykr(config: TrustDeskConfig):
    """Try to initialize StrykrClient; return None if key not configured."""
    if not config.prism_api_key:
        logger.warning("PRISM_API_KEY not set — Strykr/PRISM disabled")
        return None
    from trustdesk.adapters.strykr.client import StrykrClient
    return StrykrClient(config.prism_api_key)


def main() -> None:
    """Start the TrustDesk desk process."""
    setup_logging()
    config = TrustDeskConfig()

    logger.info("Starting TrustDesk desk in %s mode", config.mode)

    # -- Adapters (graceful degradation if keys not set) --
    kraken = KrakenClient(config)
    anthropic = _try_anthropic(config)
    chain = _try_chain(config)
    ipfs = _try_ipfs(config)
    _strykr = _try_strykr(config)

    # -- Event bus for WebSocket --
    event_bus = EventBus()

    # -- Modules --
    signal_engine = SignalEngine(provider=kraken)
    strategist = Strategist(client=anthropic) if anthropic else None
    reputation_engine = ReputationEngine()
    circuit_breaker = CircuitBreaker()

    # Risk manager needs reputation engine, circuit breaker, and LLM evaluator
    risk_manager = RiskManager(
        reputation_engine=reputation_engine,
        circuit_breaker=circuit_breaker,
        llm_evaluator=anthropic,
    )

    # Auditor needs chain + IPFS
    auditor = None
    if chain and ipfs:
        from trustdesk.auditor.auditor import Auditor
        auditor = Auditor(chain_adapter=chain, ipfs_adapter=ipfs)
    else:
        logger.warning("Auditor disabled — chain or IPFS not configured")

    # -- Build orchestrator graph --
    graph = build_graph(
        engine=signal_engine,
        strategist=strategist,
        signal_cls=SignalPayload,
        reputation_engine=reputation_engine,
        risk_manager=risk_manager,
        queue=None,
        kraken=kraken,
        auditor=auditor,
    )

    # -- FastAPI app --
    app = create_app(event_bus=event_bus)
    app.state.graph = graph
    app.state.config = config

    logger.info("Desk ready. API at http://localhost:8000")
    logger.info("Dashboard: cd dashboard && npm run dev")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
