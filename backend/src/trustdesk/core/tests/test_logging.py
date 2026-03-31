import structlog

from trustdesk.core.logging import (
    bind_correlation_id,
    clear_correlation_id,
    get_logger,
    setup_logging,
)


def test_get_logger_returns_bound_logger() -> None:
    setup_logging()
    logger = get_logger("risk_manager")
    assert isinstance(logger, structlog.stdlib.BoundLogger)


def test_logger_binds_module_name() -> None:
    setup_logging()
    logger = get_logger("signal_engine")
    ctx = structlog.get_context(logger)
    assert ctx["module"] == "signal_engine"


def test_setup_logging_json_output() -> None:
    """setup_logging with json_output=True uses JSONRenderer (no error)."""
    setup_logging(json_output=True)
    logger = get_logger("json_test")
    assert isinstance(logger, structlog.stdlib.BoundLogger)


def test_bind_correlation_id() -> None:
    """bind_correlation_id stores the ID in context vars."""
    structlog.contextvars.clear_contextvars()
    bind_correlation_id("corr-abc-123")
    ctx = structlog.contextvars.get_contextvars()
    assert ctx["correlation_id"] == "corr-abc-123"
    structlog.contextvars.clear_contextvars()


def test_clear_correlation_id() -> None:
    """clear_correlation_id removes the correlation_id from context vars."""
    structlog.contextvars.clear_contextvars()
    bind_correlation_id("corr-xyz-456")
    clear_correlation_id()
    ctx = structlog.contextvars.get_contextvars()
    assert "correlation_id" not in ctx
