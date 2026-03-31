from datetime import datetime

from sqlalchemy import inspect

from trustdesk.core.models import Base, RetryQueue, Signal, Trade


def test_trade_table_name() -> None:
    assert Trade.__tablename__ == "trades"


def test_signal_table_name() -> None:
    assert Signal.__tablename__ == "signals"


def test_retry_queue_table_name() -> None:
    assert RetryQueue.__tablename__ == "retry_queue"


def test_trade_columns_exist() -> None:
    mapper = inspect(Trade)
    col_names = {c.key for c in mapper.column_attrs}
    required = {"id", "proposal_id", "agent_id", "pair", "action", "status", "created_at"}
    assert required.issubset(col_names)


def test_all_models_share_base() -> None:
    tables = Base.metadata.tables
    assert "trades" in tables
    assert "signals" in tables
    assert "retry_queue" in tables


def test_trade_created_at_default() -> None:
    """Exercise the lambda default for Trade.created_at."""
    # SQLAlchemy ColumnDefault lambdas receive a context arg; pass None for unit testing
    col = Trade.__table__.c.created_at
    default_val = col.default.arg(None)
    assert isinstance(default_val, datetime)
    assert default_val.tzinfo is not None


def test_signal_created_at_default() -> None:
    """Exercise the lambda default for Signal.created_at."""
    col = Signal.__table__.c.created_at
    default_val = col.default.arg(None)
    assert isinstance(default_val, datetime)
    assert default_val.tzinfo is not None


def test_retry_queue_created_at_default() -> None:
    """Exercise the lambda default for RetryQueue.created_at."""
    col = RetryQueue.__table__.c.created_at
    default_val = col.default.arg(None)
    assert isinstance(default_val, datetime)
    assert default_val.tzinfo is not None


def test_trade_status_default() -> None:
    """Trade.status column default is 'proposed'."""
    col = Trade.__table__.c.status
    assert col.default.arg == "proposed"


def test_retry_queue_attempts_default() -> None:
    """RetryQueue.attempts column default is 0."""
    col = RetryQueue.__table__.c.attempts
    assert col.default.arg == 0


def test_trade_nullable_fields() -> None:
    """Optional fields are nullable."""
    mapper = inspect(Trade)
    col_map = {c.key: c for c in mapper.column_attrs}
    nullable_fields = {
        "entry_price", "exit_price", "take_profit_2", "verdict",
        "tier_at_trade", "realized_pnl", "proposal_json", "verdict_json",
        "evidence_uri", "on_chain_tx", "correlation_id", "closed_at",
    }
    for field in nullable_fields:
        assert field in col_map, f"Missing field: {field}"


def test_signal_columns_exist() -> None:
    """Signal model has all required columns."""
    mapper = inspect(Signal)
    col_names = {c.key for c in mapper.column_attrs}
    required = {"id", "pair", "regime", "alignment_score", "alignment_grade", "payload_json", "created_at"}
    assert required.issubset(col_names)


def test_retry_queue_columns_exist() -> None:
    """RetryQueue model has all required columns."""
    mapper = inspect(RetryQueue)
    col_names = {c.key for c in mapper.column_attrs}
    required = {"id", "operation", "payload_json", "attempts", "last_error", "created_at", "next_retry_at"}
    assert required.issubset(col_names)
