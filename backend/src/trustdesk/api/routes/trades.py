"""Trade history and portfolio endpoints."""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _get_trades(request: Request) -> list[dict]:
    """Get trades from app state (DB in production)."""
    return getattr(request.app.state, "trades", [])


@router.get("/trades")
async def list_trades(request: Request) -> list[dict]:
    """Return all trade history."""
    return _get_trades(request)


@router.get("/trades/{proposal_id}")
async def get_trade(proposal_id: str, request: Request) -> dict:
    """Return a single trade by proposal ID."""
    trades = _get_trades(request)
    for trade in trades:
        if trade["proposal_id"] == proposal_id:
            return trade
    raise HTTPException(status_code=404, detail=f"Trade {proposal_id} not found")


@router.get("/portfolio")
async def get_portfolio(request: Request) -> dict:
    """Return current portfolio summary."""
    trades = _get_trades(request)
    executed = [t for t in trades if t.get("status") == "executed"]
    total_pnl = sum(t.get("pnl", 0.0) for t in executed)
    return {
        "positions": executed,
        "nav": 10000.0 + total_pnl,
        "unrealized_pnl": total_pnl,
    }
