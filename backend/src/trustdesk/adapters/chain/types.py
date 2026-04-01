"""Types for the chain adapter."""
from __future__ import annotations

from enum import Enum

# Thresholds in ETH
_THRESHOLD_NORMAL = 0.1
_THRESHOLD_REDUCED = 0.05
_THRESHOLD_CRITICAL = 0.01


class WritePriority(Enum):
    """Gas-based write priority tiers."""

    NORMAL = "normal"
    REDUCED = "reduced"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


def get_write_priority(balance_eth: float) -> WritePriority:
    """Determine write priority based on ETH balance.

    Thresholds:
        > 0.1 ETH  -> NORMAL
        0.05-0.1   -> REDUCED
        0.01-0.05  -> CRITICAL
        < 0.01     -> EMERGENCY
    """
    if balance_eth > _THRESHOLD_NORMAL:
        return WritePriority.NORMAL
    if balance_eth >= _THRESHOLD_REDUCED:
        return WritePriority.REDUCED
    if balance_eth >= _THRESHOLD_CRITICAL:
        return WritePriority.CRITICAL
    return WritePriority.EMERGENCY
