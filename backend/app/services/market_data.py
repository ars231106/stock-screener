"""Alpha Vantage access with a Supabase-backed shared cache.

Why the cache matters: the Alpha Vantage free tier allows roughly 25
requests per day per key. Without caching, a handful of page loads would
exhaust it. Every quote and symbol search is therefore written to Postgres
and served from there until it goes stale.

The API key lives only here, on the server. It is never sent to the browser
(the original client-side version shipped the key in script.js).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.supabase_client import get_supabase

log = logging.getLogger(__name__)

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "CHF": "CHF",
    "CNY": "¥",
    "HKD": "HK$",
    "SGD": "S$",
    "KRW": "₩",
    "BRL": "R$",
    "ZAR": "R",
}


class MarketDataError(Exception):
    """Raised when upstream data cannot be obtained."""


class RateLimitError(MarketDataError):
    """Upstream provider refused because of its rate limit."""


def currency_symbol(code: Optional[str]) -> str:
    if not code:
        return ""
    return CURRENCY_SYMBOLS.get(code.upper(), code.upper())


def _is_fresh(fetched_at: str, ttl_seconds: int) -> bool:
    try:
        ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts < timedelta(seconds=ttl_seconds)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
def _cache_get(table: str, key_col: str, key: str, ttl: int) -> Optional[dict]:
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = (
            sb.table(table)
            .select("payload, fetched_at")
            .eq(key_col, key)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # cache must never break the request
        log.warning("cache read failed for %s/%s: %s", table, key, exc)
        return None
    rows = res.data or []
    if not rows:
        return None
    row = rows[0]
    if not _is_fresh(row.get("fetched_at", ""), ttl):
        return None
    return row.get("payload")


def _cache_put(table: str, key_col: str, key: str, payload: dict) -> None:
    sb = get_supabase()
    if sb is None:
        return
    try:
        sb.table(table).upsert(
            {
                key_col: key,
                "payload": payload,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as exc:
        log.warning("cache write failed for %s/%s: %s", table, key, exc)


def _cache_get_stale(table: str, key_col: str, key: str) -> Optional[dict]:
    """Last-resort read that ignores TTL — used when the upstream API is
    rate-limited so the user still sees data rather than an error."""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = (
            sb.table(table).select("payload").eq(key_col, key).limit(1).execute()
        )
    except Exception:
        return None
    rows = res.data or []
    return rows[0].get("payload") if rows else None


# ---------------------------------------------------------------------------
# Upstream calls
# ---------------------------------------------------------------------------
async def _call_alpha_vantage(params: Dict[str, str]) -> Dict[str, Any]:
    params = {**params, "apikey": settings.alpha_vantage_key}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(settings.alpha_vantage_base, params=params)
        except httpx.HTTPError as exc:
            raise MarketDataError(f"Upstream request failed: {exc}") from exc

    if resp.status_code != 200:
        raise MarketDataError(f"Upstream returned HTTP {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise MarketDataError("Upstream returned a non-JSON response") from exc

    # Alpha Vantage signals throttling in the body, not the status code.
    if "Note" in data or "Information" in data:
        raise RateLimitError(data.get("Note") or data.get("Information", ""))
    if "Error Message" in data:
        raise MarketDataError(data["Error Message"])
    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def search_symbols(query: str) -> List[Dict[str, Any]]:
    """Return normalised search matches for a company name or ticker."""
    key = query.strip().lower()
    if not key:
        return []

    cached = _cache_get(
        "symbol_search_cache", "query", key, settings.search_cache_ttl
    )
    if cached is not None:
        return cached.get("matches", [])

    try:
        raw = await _call_alpha_vantage(
            {"function": "SYMBOL_SEARCH", "keywords": query}
        )
    except RateLimitError:
        stale = _cache_get_stale("symbol_search_cache", "query", key)
        if stale is not None:
            return stale.get("matches", [])
        raise

    matches = [
        {
            "symbol": m.get("1. symbol"),
            "name": m.get("2. name"),
            "type": m.get("3. type"),
            "region": m.get("4. region"),
            "currency": m.get("8. currency"),
            "match_score": float(m.get("9. matchScore", 0) or 0),
        }
        for m in raw.get("bestMatches", [])
        if m.get("1. symbol")
    ]

    _cache_put("symbol_search_cache", "query", key, {"matches": matches})
    return matches


async def get_quote(symbol: str) -> Dict[str, Any]:
    """Return a normalised global quote for a ticker."""
    key = symbol.strip().upper()
    if not key:
        raise MarketDataError("Symbol is required")

    cached = _cache_get("quote_cache", "symbol", key, settings.quote_cache_ttl)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        raw = await _call_alpha_vantage(
            {"function": "GLOBAL_QUOTE", "symbol": key}
        )
    except RateLimitError:
        stale = _cache_get_stale("quote_cache", "symbol", key)
        if stale is not None:
            return {**stale, "cached": True, "stale": True}
        raise

    q = raw.get("Global Quote") or {}
    if not q.get("01. symbol"):
        raise MarketDataError(f"No quote data available for {key}")

    def num(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    quote = {
        "symbol": q.get("01. symbol"),
        "open": num(q.get("02. open")),
        "high": num(q.get("03. high")),
        "low": num(q.get("04. low")),
        "price": num(q.get("05. price")),
        "volume": int(q.get("06. volume") or 0),
        "latest_trading_day": q.get("07. latest trading day"),
        "previous_close": num(q.get("08. previous close")),
        "change": num(q.get("09. change")),
        "change_percent": (q.get("10. change percent") or "").strip(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    _cache_put("quote_cache", "symbol", key, quote)
    return {**quote, "cached": False}


async def get_overview(symbol: str) -> Dict[str, Any]:
    """Company fundamentals — P/E, market cap, margins, dividend yield.

    These are the fields the screener criteria are evaluated against.
    """
    key = symbol.strip().upper()
    cache_key = f"overview:{key}"

    cached = _cache_get("quote_cache", "symbol", cache_key, 86400)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        raw = await _call_alpha_vantage({"function": "OVERVIEW", "symbol": key})
    except RateLimitError:
        stale = _cache_get_stale("quote_cache", "symbol", cache_key)
        if stale is not None:
            return {**stale, "cached": True, "stale": True}
        raise

    if not raw or not raw.get("Symbol"):
        raise MarketDataError(f"No fundamentals available for {key}")

    def num(value: Any) -> Optional[float]:
        if value in (None, "None", "-", ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    overview = {
        "symbol": raw.get("Symbol"),
        "name": raw.get("Name"),
        "description": raw.get("Description"),
        "exchange": raw.get("Exchange"),
        "currency": raw.get("Currency"),
        "country": raw.get("Country"),
        "sector": raw.get("Sector"),
        "industry": raw.get("Industry"),
        "market_cap": num(raw.get("MarketCapitalization")),
        "pe_ratio": num(raw.get("PERatio")),
        "peg_ratio": num(raw.get("PEGRatio")),
        "pb_ratio": num(raw.get("PriceToBookRatio")),
        "eps": num(raw.get("EPS")),
        "book_value": num(raw.get("BookValue")),
        "dividend_yield": num(raw.get("DividendYield")),
        "dividend_per_share": num(raw.get("DividendPerShare")),
        "profit_margin": num(raw.get("ProfitMargin")),
        "operating_margin": num(raw.get("OperatingMarginTTM")),
        "roe": num(raw.get("ReturnOnEquityTTM")),
        "roa": num(raw.get("ReturnOnAssetsTTM")),
        "revenue_ttm": num(raw.get("RevenueTTM")),
        "revenue_growth_yoy": num(raw.get("QuarterlyRevenueGrowthYOY")),
        "earnings_growth_yoy": num(raw.get("QuarterlyEarningsGrowthYOY")),
        "beta": num(raw.get("Beta")),
        "week_52_high": num(raw.get("52WeekHigh")),
        "week_52_low": num(raw.get("52WeekLow")),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    _cache_put("quote_cache", "symbol", cache_key, overview)
    return {**overview, "cached": False}
