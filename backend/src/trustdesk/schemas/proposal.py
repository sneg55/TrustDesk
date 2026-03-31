"""TradeProposal — submitted by any agent through the Agent Interface."""
from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Literal

from pydantic import BaseModel


class TradeProposal(BaseModel):
    agent_id: str
    proposal_id: str
    timestamp: datetime
    action: Literal["BUY", "SELL"]
    pair: str
    size_pct: float
    entry_price_limit: float
    entry_type: Literal["LIMIT"] = "LIMIT"
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None = None
    time_horizon: str
    reasoning: str
    invalidation: str
    alignment_score: float | None = None
    alignment_grade: Literal["STRONG", "MODERATE", "WEAK", "NO_SIGNAL"] | None = None
    override_justification: str | None = None
    regime_at_proposal: Literal["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE"] | None = None
    signals_cited: list[str] | None = None
