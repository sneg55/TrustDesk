"""Gas balance monitor with tiered write priorities."""
from __future__ import annotations

from typing import Any

from trustdesk.adapters.chain.types import WritePriority, get_write_priority
from trustdesk.core.logging import get_logger

log = get_logger(__name__)

# Priority ordering: lower index = more restrictive
_PRIORITY_ORDER = [
    WritePriority.EMERGENCY,
    WritePriority.CRITICAL,
    WritePriority.REDUCED,
    WritePriority.NORMAL,
]


class GasMonitor:
    """Monitor gas balance and gate writes based on priority."""

    def __init__(self, w3: Any) -> None:
        self._w3 = w3

    async def check_balance(self, address: str) -> tuple[float, WritePriority]:
        """Check ETH balance and return balance + write priority.

        Returns:
            Tuple of (balance_eth, WritePriority).
        """
        balance_wei = await self._w3.eth.get_balance(address)
        balance_eth = self._w3.from_wei(balance_wei, "ether")
        priority = get_write_priority(balance_eth)
        log.info("gas_check", address=address, balance=balance_eth, priority=priority.value)
        return balance_eth, priority

    async def should_write(self, address: str, required_priority: WritePriority) -> bool:
        """Check if a write at the given priority level should proceed.

        A write is allowed if the wallet's current priority is at least
        as permissive as the required priority. Lower balance = more
        restrictive = only critical/emergency writes allowed.
        """
        _, current = await self.check_balance(address)
        current_idx = _PRIORITY_ORDER.index(current)
        required_idx = _PRIORITY_ORDER.index(required_priority)
        # Current must be >= required in permissiveness (higher or equal index)
        # But for emergency wallets, we allow emergency writes
        return current_idx >= required_idx
