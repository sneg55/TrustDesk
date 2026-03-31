"""SQLAlchemy models for PostgreSQL persistence."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    pair: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(4))
    size_pct: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit_1: Mapped[float] = mapped_column(Float)
    take_profit_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tier_at_trade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    proposal_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verdict_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_uri: Mapped[str | None] = mapped_column(String(256), nullable=True)
    on_chain_tx: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair: Mapped[str] = mapped_column(String(16), index=True)
    regime: Mapped[str] = mapped_column(String(16))
    alignment_score: Mapped[float] = mapped_column(Float)
    alignment_grade: Mapped[str] = mapped_column(String(16))
    payload_json: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RetryQueue(Base):
    __tablename__ = "retry_queue"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
