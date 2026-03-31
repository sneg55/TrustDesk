"""PostgreSQL connection and session factory."""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from trustdesk.core.config import TrustDeskConfig


def create_engine(config: TrustDeskConfig):
    """Create an async SQLAlchemy engine from config."""
    return create_async_engine(config.database_url, echo=False)


def create_session_factory(config: TrustDeskConfig) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    engine = create_engine(config)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
