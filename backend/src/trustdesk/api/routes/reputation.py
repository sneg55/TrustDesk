"""Reputation and tier endpoints."""
from fastapi import APIRouter, Request

router = APIRouter()

DEFAULT_REPUTATION = {
    "tier": "NOVICE",
    "score": 0,
    "total_trades": 0,
    "successful_trades": 0,
    "promotion_history": [],
}


@router.get("/reputation")
async def get_reputation(request: Request) -> dict:
    """Return current reputation summary."""
    return getattr(request.app.state, "reputation", DEFAULT_REPUTATION)
