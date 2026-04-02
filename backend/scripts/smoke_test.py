#!/usr/bin/env python3
"""Smoke test: run one full signal cycle against real Kraken paper data."""
import asyncio
import json
from trustdesk.core.config import TrustDeskConfig
from trustdesk.adapters.kraken.client import KrakenClient
from trustdesk.signal_engine.engine import SignalEngine


async def main():
    config = TrustDeskConfig()
    kraken = KrakenClient(config)

    # Optional: Strykr
    strykr = None
    if config.prism_api_key:
        from trustdesk.adapters.strykr.client import StrykrClient
        strykr = StrykrClient(config.prism_api_key)

    engine = SignalEngine(provider=kraken, strykr=strykr)

    print("Running signal cycle for BTC/USD...")
    try:
        signal = await engine.run_cycle("BTC/USD")
        print(json.dumps(signal.model_dump(mode="json"), indent=2, default=str))
    except Exception as e:
        print(f"Signal cycle failed: {e}")
        print("Make sure Kraken CLI is installed: kraken status")

    if strykr:
        await strykr.close()


if __name__ == "__main__":
    asyncio.run(main())
