import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.db import first as db_first
from app.core.security import CurrentUser, get_optional_user
from app.core.supabase_client import get_supabase
from app.schemas import Overview, PriceHistory, Quote, SearchResponse, StockDetail
from app.services import fundamentals, market_data
from app.services.market_data import MarketDataError, RateLimitError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def _upstream_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Market data rate limit reached. Alpha Vantage's free tier "
                "allows a limited number of requests per day — try again "
                "shortly, or add your own key."
            ),
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc) or "Upstream error"
    )


def _record_search(
    user: CurrentUser | None, query: str, symbol: str | None, name: str | None
) -> None:
    if user is None:
        return
    sb = get_supabase()
    if sb is None:
        return
    try:
        sb.table("search_history").insert(
            {
                "user_id": user.id,
                "query": query,
                "symbol": symbol,
                "company_name": name,
            }
        ).execute()
    except Exception as exc:
        log.warning("failed to record search history: %s", exc)


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=80, description="Company name or ticker"),
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Search for companies by name or ticker symbol."""
    try:
        matches = await market_data.search_symbols(q)
    except MarketDataError as exc:
        raise _upstream_error(exc) from exc

    if matches:
        top = matches[0]
        _record_search(user, q, top.get("symbol"), top.get("name"))

    # Validate rather than trust: the provider layer returns plain dicts and
    # this is the boundary where they become part of our API contract.
    return SearchResponse.model_validate({"query": q, "matches": matches})


@router.get("/{symbol}/quote", response_model=Quote)
async def quote(symbol: str):
    """Latest price snapshot for a ticker."""
    try:
        return await market_data.get_quote(symbol)
    except MarketDataError as exc:
        raise _upstream_error(exc) from exc


@router.get("/{symbol}/overview", response_model=Overview)
async def overview(symbol: str):
    """Company fundamentals for a ticker."""
    try:
        return await market_data.get_overview(symbol)
    except MarketDataError as exc:
        raise _upstream_error(exc) from exc


@router.get("/{symbol}/history", response_model=PriceHistory)
async def history(
    symbol: str,
    range: str = Query(
        "1y",
        pattern="^(1m|6m|1y|3y|5y|10y|max)$",
        description="1m, 6m, 1y, 3y, 5y, 10y or max",
    ),
):
    """OHLCV candles plus 50- and 200-period moving averages."""
    try:
        return await market_data.get_history(symbol, range)
    except MarketDataError as exc:
        raise _upstream_error(exc) from exc


@router.get("/{symbol}", response_model=StockDetail)
async def detail(
    symbol: str,
    user: CurrentUser | None = Depends(get_optional_user),
):
    """Everything the stock detail page needs in a single round-trip:
    quote, fundamentals where available, and whether this ticker is already
    on the signed-in user's watchlist."""
    sym = symbol.strip().upper()

    try:
        quote_data = await market_data.get_quote(sym)
    except MarketDataError as exc:
        raise _upstream_error(exc) from exc

    # Fundamentals come from the stored table, which the scheduled refresh
    # job populates. The API server cannot fetch them live on Render --
    # Yahoo blocks its fundamentals endpoint from that IP range -- so the
    # stored read is the only path that works in production.
    overview_data = await fundamentals.get_overview(sym)

    currency = (overview_data or {}).get("currency")
    name = (overview_data or {}).get("name")
    region = (overview_data or {}).get("country")

    # Fall back to the search index for the display name when there are
    # no fundamentals.
    if not name:
        try:
            matches = await market_data.search_symbols(sym)
            for m in matches:
                if (m.get("symbol") or "").upper() == sym:
                    name = m.get("name")
                    region = region or m.get("region")
                    currency = currency or m.get("currency")
                    break
        except MarketDataError:
            pass

    in_watchlist = False
    sb = get_supabase()
    if user is not None and sb is not None:
        try:
            res = (
                sb.table("watchlist_items")
                .select("id")
                .eq("user_id", user.id)
                .eq("symbol", sym)
                .limit(1)
                .execute()
            )
            in_watchlist = db_first(res) is not None
        except Exception as exc:
            log.warning("watchlist lookup failed: %s", exc)

    return StockDetail.model_validate(
        {
            "symbol": sym,
            "name": name,
            "region": region,
            "currency": currency,
            "currency_symbol": market_data.currency_symbol(currency),
            "quote": quote_data,
            "overview": overview_data,
            "in_watchlist": in_watchlist,
        }
    )
