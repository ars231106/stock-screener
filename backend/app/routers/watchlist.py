import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import CurrentUser, get_current_user
from app.core.supabase_client import require_supabase
from app.schemas import WatchlistItem, WatchlistItemCreate, WatchlistItemWithQuote
from app.services import market_data
from app.services.market_data import MarketDataError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _default_watchlist_id(user: CurrentUser) -> str:
    """Return the user's default watchlist, creating it on first use."""
    sb = require_supabase()
    res = (
        sb.table("watchlists")
        .select("id")
        .eq("user_id", user.id)
        .eq("is_default", True)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]["id"]

    created = (
        sb.table("watchlists")
        .insert({"user_id": user.id, "name": "My Watchlist", "is_default": True})
        .execute()
    )
    if not created.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create a watchlist",
        )
    return created.data[0]["id"]


@router.get("", response_model=List[WatchlistItemWithQuote])
async def list_watchlist(
    with_quotes: bool = Query(True, description="Attach a live quote to each row"),
    user: CurrentUser = Depends(get_current_user),
):
    """Every symbol the signed-in user is following."""
    sb = require_supabase()
    res = (
        sb.table("watchlist_items")
        .select("*")
        .eq("user_id", user.id)
        .order("added_at", desc=True)
        .execute()
    )
    rows = res.data or []

    if not with_quotes:
        return rows

    enriched = []
    for row in rows:
        quote = None
        try:
            quote = await market_data.get_quote(row["symbol"])
        except MarketDataError as exc:
            # A rate-limited or missing quote should not blank the watchlist.
            log.info("quote unavailable for %s: %s", row["symbol"], exc)
        enriched.append({**row, "quote": quote})
    return enriched


@router.post("", response_model=WatchlistItem, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    payload: WatchlistItemCreate,
    user: CurrentUser = Depends(get_current_user),
):
    """Add a ticker. Adding one that is already there is a no-op, not an error."""
    sb = require_supabase()
    watchlist_id = _default_watchlist_id(user)
    symbol = payload.symbol.strip().upper()

    existing = (
        sb.table("watchlist_items")
        .select("*")
        .eq("watchlist_id", watchlist_id)
        .eq("symbol", symbol)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    res = (
        sb.table("watchlist_items")
        .insert(
            {
                "watchlist_id": watchlist_id,
                "user_id": user.id,
                "symbol": symbol,
                "company_name": payload.company_name,
                "region": payload.region,
                "currency": payload.currency,
                "notes": payload.notes,
            }
        )
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add to watchlist",
        )
    return res.data[0]


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    symbol: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Stop following a ticker."""
    sb = require_supabase()
    (
        sb.table("watchlist_items")
        .delete()
        .eq("user_id", user.id)
        .eq("symbol", symbol.strip().upper())
        .execute()
    )
    return None
