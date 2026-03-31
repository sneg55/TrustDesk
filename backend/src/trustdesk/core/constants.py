"""Global constants. Domain-specific constants live in their module's constants.py."""

SUPPORTED_PAIRS: tuple[str, ...] = ("BTC/USD", "ETH/USD", "SOL/USD")

REGIMES: tuple[str, ...] = ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE")

TIERS: tuple[str, ...] = ("UNPROVEN", "ESTABLISHED", "TRUSTED")

VERDICTS: tuple[str, ...] = (
    "APPROVED",
    "APPROVED_WITH_MODIFICATION",
    "APPROVED_HARD_ONLY",
    "REJECTED",
)

ALIGNMENT_GRADES: tuple[str, ...] = ("STRONG", "MODERATE", "WEAK", "NO_SIGNAL")

# Next ID: 1007
ERROR_IDS: dict[str, int] = {
    "KRAKEN_CONNECTION": 1001,
    "KRAKEN_COMMAND": 1002,
    "CHAIN_RPC": 1003,
    "CHAIN_TX_FAILED": 1004,
    "LLM_UNAVAILABLE": 1005,
    "IPFS_UPLOAD": 1006,
}
