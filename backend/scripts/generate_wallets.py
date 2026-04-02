#!/usr/bin/env python3
"""Generate two Base Sepolia wallets for TrustDesk."""
from eth_account import Account
import secrets

agent = Account.from_key(secrets.token_hex(32))
validator = Account.from_key(secrets.token_hex(32))

print("=== TrustDesk Wallets ===")
print(f"\nAgent wallet:")
print(f"  Address: {agent.address}")
print(f"  Private key: {agent.key.hex()}")
print(f"\nValidator wallet:")
print(f"  Address: {validator.address}")
print(f"  Private key: {validator.key.hex()}")
print(f"\nAdd to .env:")
print(f"TRUSTDESK_AGENT_PRIVATE_KEY={agent.key.hex()}")
print(f"TRUSTDESK_VALIDATOR_PRIVATE_KEY={validator.key.hex()}")
print(f"\nFund both addresses with testnet ETH from:")
print(f"  https://www.alchemy.com/faucets/base-sepolia")
print(f"  https://faucets.chain.link")
