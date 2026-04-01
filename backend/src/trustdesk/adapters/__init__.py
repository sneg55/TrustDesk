"""External service adapters."""

from trustdesk.adapters.anthropic import AnthropicClient
from trustdesk.adapters.chain import ChainClient
from trustdesk.adapters.ipfs import IPFSClient
from trustdesk.adapters.kraken import KrakenClient

__all__ = ["AnthropicClient", "ChainClient", "IPFSClient", "KrakenClient"]
