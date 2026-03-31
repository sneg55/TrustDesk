import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from trustdesk.core.db import create_engine, create_session_factory


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch):
    """Config with a fake but syntactically valid async database URL."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
    from trustdesk.core.config import TrustDeskConfig
    return TrustDeskConfig()


def test_create_engine_returns_async_engine(config) -> None:
    """create_engine returns an AsyncEngine instance."""
    engine = create_engine(config)
    assert isinstance(engine, AsyncEngine)


def test_create_engine_uses_config_url(config) -> None:
    """create_engine uses the database_url from config."""
    engine = create_engine(config)
    assert "localhost" in str(engine.url)
    assert "testdb" in str(engine.url)


def test_create_session_factory_returns_sessionmaker(config) -> None:
    """create_session_factory returns an async_sessionmaker."""
    factory = create_session_factory(config)
    assert isinstance(factory, async_sessionmaker)


def test_create_session_factory_produces_async_sessions(config) -> None:
    """Sessions produced by the factory are AsyncSession instances."""
    factory = create_session_factory(config)
    # async_sessionmaker.class_ should be AsyncSession
    assert factory.class_ is AsyncSession


def test_create_session_factory_expire_on_commit_false(config) -> None:
    """Sessions are configured with expire_on_commit=False."""
    factory = create_session_factory(config)
    assert factory.kw.get("expire_on_commit") is False
