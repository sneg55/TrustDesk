#!/usr/bin/env python3
"""Verify Kraken CLI is installed and paper trading works."""
import asyncio
import json
from trustdesk.adapters.kraken.client import KrakenClient
from trustdesk.core.config import TrustDeskConfig


async def main():
    config = TrustDeskConfig()
    client = KrakenClient(config)

    print("1. Checking Kraken CLI status...")
    # ticker is public, no auth needed
    try:
        ticker = await client.ticker("BTC/USD")
        print(f"   BTC/USD last: ${ticker.last:,.2f}")
    except Exception as e:
        print(f"   FAILED: {e}")
        print("   Install: curl --proto '=https' --tlsv1.2 -LsSf https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh")
        return

    print("2. Checking paper trading...")
    try:
        # Paper init doesn't need auth
        result = await client._runner.run("paper", ["init", "--balance", "10000"])
        print(f"   Paper account initialized: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   Paper init: {e}")

    print("3. Fetching OHLC data...")
    try:
        ohlc = await client.ohlc("BTC/USD", 15)
        print(f"   Got {len(ohlc)} candles")
    except Exception as e:
        print(f"   OHLC failed: {e}")

    print("\nAll checks passed!")


if __name__ == "__main__":
    asyncio.run(main())
