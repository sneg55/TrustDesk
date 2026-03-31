"""Error hierarchy and safe extraction helpers."""

from __future__ import annotations


class TrustDeskError(Exception):
    """Base error for all TrustDesk exceptions."""

    def __init__(self, message: str = "", *, error_id: int = 0) -> None:
        super().__init__(message)
        self.error_id = error_id


class KrakenError(TrustDeskError):
    """Kraken CLI communication failure."""


class ChainError(TrustDeskError):
    """Blockchain / web3 interaction failure."""


class LLMUnavailableError(TrustDeskError):
    """Anthropic API unreachable or rate-limited."""


class IPFSError(TrustDeskError):
    """IPFS / Pinata upload failure."""


class ValidationError(TrustDeskError):
    """Schema or input validation failure."""


class RiskCheckFailedError(TrustDeskError):
    """Hard limit breach — trade must be rejected."""


# Backward-compatible alias
RiskCheckFailed = RiskCheckFailedError


def error_message(exc: object) -> str:
    """Safely extract a human-readable message from any value."""
    if isinstance(exc, Exception):
        return str(exc)
    return str(exc)


def to_error(exc: Exception) -> TrustDeskError:
    """Wrap any exception as a TrustDeskError, or pass through if already one."""
    if isinstance(exc, TrustDeskError):
        return exc
    wrapped = TrustDeskError(str(exc))
    wrapped.__cause__ = exc
    return wrapped
