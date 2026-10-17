"""Reads stored fundamentals.

The API server reads this table and never fetches fundamentals from a
provider itself -- Yahoo blocks its fundamentals endpoint from Render's IP
range, so a live fetch would fail there every time. jobs/refresh_fundamentals.py
populates the table from a host that can reach the provider.

A live fetch is still attempted as a last resort, which is what makes local
development work before the table has ever been seeded.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.db import first as db_first
from app.core.supabase_client import get_supabase
from app.services import market_data
from app.services.market_data import MarketDataError

log = logging.getLogger(__name__)

COLUMNS = (
    "symbol, name, exchange, currency, country, sector, industry, description, "
    "market_cap, pe_ratio, peg_ratio, pb_ratio, eps, book_value, dividend_yield, "
    "dividend_per_share, profit_margin, operating_margin, roe, roa, revenue_ttm, "
    "revenue_growth_yoy, earnings_growth_yoy, beta, week_52_high, week_52_low, "
    "updated_at"
)


def get_stored(symbol: str) -> dict[str, Any] | None:
    """Fundamentals for one symbol from the table, or None."""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = (
            sb.table("fundamentals").select(COLUMNS)
            .eq("symbol", symbol.strip().upper()).limit(1).execute()
        )
    except Exception as exc:
        log.warning("fundamentals lookup failed for %s: %s", symbol, exc)
        return None
    return db_first(res)


async def get_overview(symbol: str) -> dict[str, Any] | None:
    """Stored fundamentals, falling back to a live provider fetch.

    Returns None rather than raising: a stock page without fundamentals is
    still worth rendering, and many tickers legitimately have none.
    """
    stored = get_stored(symbol)
    if stored is not None:
        return {**stored, "cached": True}

    try:
        return await market_data.get_overview(symbol)
    except MarketDataError as exc:
        log.info("no fundamentals for %s: %s", symbol, exc)
        return None
