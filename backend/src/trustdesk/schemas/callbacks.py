"""Position lifecycle callbacks — sent from desk to connected agents."""
from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any, Literal

from pydantic import BaseModel


class PositionCallback(BaseModel):
    event: Literal["FILLED", "PARTIAL_EXIT", "STOP_TRIGGERED", "TIME_EXIT", "INVALIDATION_EXIT", "DEMOTION"]
    proposal_id: str
    timestamp: datetime
    details: dict[str, Any]
