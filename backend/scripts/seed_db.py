#!/usr/bin/env python3
"""Create all database tables."""
import asyncio
from trustdesk.core.config import TrustDeskConfig
from trustdesk.core.db import create_engine
from trustdesk.core.models import Base


async def seed():
    config = TrustDeskConfig()
    engine = create_engine(config)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created:", list(Base.metadata.tables.keys()))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
