from trustdesk.core.errors import (
    ChainError,
    IPFSError,
    KrakenError,
    LLMUnavailableError,
    RiskCheckFailedError,
    TrustDeskError,
    ValidationError,
    error_message,
    to_error,
)


def test_error_hierarchy() -> None:
    assert issubclass(KrakenError, TrustDeskError)
    assert issubclass(ChainError, TrustDeskError)
    assert issubclass(LLMUnavailableError, TrustDeskError)
    assert issubclass(IPFSError, TrustDeskError)
    assert issubclass(ValidationError, TrustDeskError)
    assert issubclass(RiskCheckFailedError, TrustDeskError)


def test_error_message_from_exception() -> None:
    assert error_message(ValueError("bad input")) == "bad input"


def test_error_message_from_string() -> None:
    assert error_message("raw error") == "raw error"


def test_error_message_from_unknown() -> None:
    assert error_message(42) == "42"


def test_to_error_wraps_non_trustdesk_exception() -> None:
    original = ValueError("bad")
    wrapped = to_error(original)
    assert isinstance(wrapped, TrustDeskError)
    assert wrapped.__cause__ is original


def test_to_error_passes_through_trustdesk_error() -> None:
    original = KrakenError("connection failed")
    result = to_error(original)
    assert result is original


def test_error_has_error_id() -> None:
    err = KrakenError("fail", error_id=1001)
    assert err.error_id == 1001


def test_error_default_error_id() -> None:
    """Default error_id is 0 when not specified."""
    err = TrustDeskError("something went wrong")
    assert err.error_id == 0


def test_trustdesk_error_message() -> None:
    """TrustDeskError stores the message correctly."""
    err = TrustDeskError("base error")
    assert str(err) == "base error"
