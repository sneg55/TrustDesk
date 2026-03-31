"""Structured logging with correlation IDs."""

from __future__ import annotations

import structlog


def setup_logging(json_output: bool = False) -> None:
    """Configure structlog. Call once at startup."""
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(module: str) -> structlog.stdlib.BoundLogger:
    """Get a logger with the module name pre-bound."""
    return structlog.get_logger(module=module).bind()


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the current context (async-safe via contextvars)."""
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    structlog.contextvars.unbind_contextvars("correlation_id")
