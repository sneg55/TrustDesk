"""Reputation types — feedback entries and tier definitions."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ReputationFeedback(BaseModel):
    type: Literal["TRADE_OPENED", "TRADE_UPDATE", "TRADE_CLOSED", "PASS_SUMMARY", "RISK_ADJUST"]
    score: int
    tag: str
    skill: str
    evidence_uri: str
    context: dict[str, Any]


class TierDefinition(BaseModel):
    tier: Literal["UNPROVEN", "ESTABLISHED", "TRUSTED"]
    capital_allocation: float
    max_position_pct: float
    max_open_trades: int
    max_daily_loss_pct: float
