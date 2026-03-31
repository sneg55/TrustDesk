import os

import pytest

from trustdesk.core.config import TrustDeskConfig


def test_default_config_loads_paper_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config defaults to paper mode when TRUSTDESK_MODE is not set."""
    monkeypatch.delenv("TRUSTDESK_MODE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.mode == "paper"


def test_config_reads_mode_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config reads TRUSTDESK_MODE from environment."""
    monkeypatch.setenv("TRUSTDESK_MODE", "live")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.mode == "live"


def test_config_optional_kraken_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kraken API keys are optional (paper trading needs none)."""
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.kraken_api_key is None
    assert config.kraken_api_secret is None


def test_config_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM model defaults to claude-sonnet-4-20250514."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.llm_model == "claude-sonnet-4-20250514"


def test_config_rpc_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """RPC URL defaults to Base Sepolia."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    config = TrustDeskConfig()
    assert config.rpc_url == "https://sepolia.base.org"


def test_config_agent_private_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """agent_private_key property returns trustdesk_agent_private_key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TRUSTDESK_AGENT_PRIVATE_KEY", "0xdeadbeef")
    config = TrustDeskConfig()
    assert config.agent_private_key == "0xdeadbeef"


def test_config_validator_private_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """validator_private_key property returns trustdesk_validator_private_key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TRUSTDESK_VALIDATOR_PRIVATE_KEY", "0xcafebabe")
    config = TrustDeskConfig()
    assert config.validator_private_key == "0xcafebabe"


def test_config_kraken_mcp_enabled_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """kraken_mcp_enabled defaults to True."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.delenv("TRUSTDESK_KRAKEN_MCP", raising=False)
    config = TrustDeskConfig()
    assert config.kraken_mcp_enabled is True


def test_config_kraken_mcp_enabled_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """kraken_mcp_enabled can be set to False via env."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.setenv("TRUSTDESK_KRAKEN_MCP", "false")
    config = TrustDeskConfig()
    assert config.kraken_mcp_enabled is False


def test_config_gas_check_interval_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """gas_check_interval defaults to 1800."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.delenv("TRUSTDESK_GAS_CHECK_INTERVAL", raising=False)
    config = TrustDeskConfig()
    assert config.gas_check_interval == 1800


def test_config_signal_interval_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """signal_interval defaults to 300."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    monkeypatch.delenv("TRUSTDESK_SIGNAL_INTERVAL", raising=False)
    config = TrustDeskConfig()
    assert config.signal_interval == 300
