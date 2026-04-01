"""Centralized configuration. Never use os.environ directly elsewhere."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class TrustDeskConfig(BaseSettings):
    """Single source of truth for all TrustDesk configuration."""

    model_config = {"env_prefix": "", "case_sensitive": False}

    # Mode
    trustdesk_mode: Literal["paper", "live"] = "paper"

    # Kraken
    kraken_api_key: str | None = None
    kraken_api_secret: str | None = None
    trustdesk_kraken_mcp: bool = True

    # Anthropic
    anthropic_api_key: str = ""

    # Chain (Base Sepolia)
    trustdesk_rpc_url: str = "https://sepolia.base.org"
    trustdesk_agent_private_key: str = ""
    trustdesk_validator_private_key: str = ""

    # ERC-8004 contract addresses
    trustdesk_identity_registry: str = ""
    trustdesk_reputation_registry: str = ""
    trustdesk_validation_registry: str = ""
    trustdesk_open_validator: str = ""

    # IPFS
    pinata_api_key: str = ""
    pinata_api_secret: str = ""

    # Strykr/PRISM
    prism_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://trustdesk:trustdesk@localhost:5432/trustdesk"

    # Tuning
    trustdesk_gas_check_interval: int = 1800
    trustdesk_signal_interval: int = 300
    trustdesk_llm_model: str = "claude-sonnet-4-20250514"

    @property
    def mode(self) -> str:
        return self.trustdesk_mode

    @property
    def rpc_url(self) -> str:
        return self.trustdesk_rpc_url

    @property
    def agent_private_key(self) -> str:
        return self.trustdesk_agent_private_key

    @property
    def validator_private_key(self) -> str:
        return self.trustdesk_validator_private_key

    @property
    def llm_model(self) -> str:
        return self.trustdesk_llm_model

    @property
    def kraken_mcp_enabled(self) -> bool:
        return self.trustdesk_kraken_mcp

    @property
    def gas_check_interval(self) -> int:
        return self.trustdesk_gas_check_interval

    @property
    def signal_interval(self) -> int:
        return self.trustdesk_signal_interval
