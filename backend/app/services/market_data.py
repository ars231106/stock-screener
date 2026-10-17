"""Cached, provider-agnostic access to market data.

Responsibilities, in order:

1. Serve from the shared Postgres cache when the entry is still fresh.
2. Otherwise ask the provider chain, falling through to the next provider
   when one is rate-limited or unreachable.
3. If every provider fails, serve a stale cache entry rather than an error --
   a slightly old price beats a broken page.

The cache lives in Postgres rather than in memory because Render restarts the
process regularly and an in-memory cache would die with it. It is also shared,
so the second person to look up a ticker pays nothing for it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.core.config import settings
from app.core.supabase_client import get_supabase
from app.providers.base import ProviderError, RateLimitError
from app.providers.registry import get_provider_chain

log = logging.getLogger(__name__)

# Re-exported under the historical names so routers and the screening engine
# keep importing from one place.
MarketDataError = ProviderError
__all__ = [
    "MarketDataError",
    "RateLimitError",
    "currency_symbol",
    "get_history",
    "get_overview",
    "get_quote",
    "search_symbols",
]

CURRENCY_SYMBOLS = {
    "USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "JPY": "¥",
    "CAD": "C$", "AUD": "A$", "CHF": "CHF", "CNY": "¥", "HKD": "HK$",
    "SGD": "S$", "KRW": "₩", "BRL": "R$", "ZAR": "R", "AED": "AED",
}


def currency_symbol(code: Optional[str]) -> str:
    if not code:
        return ""
    return CURRENCY_SYMBOLS.get(code.upper(), code.upper())


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------
def _is_fresh(fetched_at: str, ttl_seconds: int) -> bool:
    try:
        ts = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts < timedelta(seconds=ttl_seconds)


def _cache_get(table: str, key_col: str, key: str, ttl: int) -> Optional[dict]:
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = (
            sb.table(table).select("payload, fetched_at")
            .eq(key_col, key).limit(1).execute()
        )
    except Exception as exc:
        log.warning("cache read failed for %s/%s: %s", table, key, exc)
        return None
    rows = res.data or []
    if not rows or not _is_fresh(rows[0].get("fetched_at", ""), ttl):
        return None
    return rows[0].get("payload")


def _cache_get_stale(table: str, key_col: str, key: str) -> Optional[dict]:
    """Ignores the TTL. Used only when every provider has failed."""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        res = sb.table(table).select("payload").eq(key_col, key).limit(1).execute()
    except Exception:
        return None
    rows = res.data or []
    return rows[0].get("payload") if rows else None


def _cache_put(table: str, key_col: str, key: str, payload: Any) -> None:
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


# --------------------------------------------------------------------------
# Provider fan-out
# --------------------------------------------------------------------------
async def _try_providers(
    call: Callable[[Any], Awaitable[Any]], what: str
) -> Any:
    """Run `call` against each provider until one answers.

    A RateLimitError or transport failure moves to the next provider. The
    last error is re-raised if nothing succeeds, so the caller can decide
    whether to fall back to a stale cache entry.
    """
    last_error: Exception = ProviderError(f"No provider could serve {what}")

    for provider in get_provider_chain():
        try:
            return await call(provider)
        except RateLimitError as exc:
            log.warning("%s rate-limited for %s: %s", provider.name, what, exc)
            last_error = exc
        except ProviderError as exc:
            log.info("%s could not serve %s: %s", provider.name, what, exc)
            last_error = exc
        except Exception as exc:  # defensive: a provider must never crash the request
            log.exception("%s raised unexpectedly for %s", provider.name, what)
            last_error = ProviderError(str(exc))

    raise last_error


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
async def search_symbols(query: str) -> List[Dict[str, Any]]:
    key = query.strip().lower()
    if not key:
        return []

    cached = _cache_get("symbol_search_cache", "query", key, settings.search_cache_ttl)
    if cached is not None:
        return cached.get("matches", [])

    try:
        matches = await _try_providers(lambda p: p.search(query), f"search:{key}")
    except ProviderError:
        stale = _cache_get_stale("symbol_search_cache", "query", key)
        if stale is not None:
            return stale.get("matches", [])
        raise

    _cache_put("symbol_search_cache", "query", key, {"matches": matches})
    return matches


async def get_quote(symbol: str) -> Dict[str, Any]:
    key = symbol.strip().upper()
    if not key:
        raise ProviderError("Symbol is required")

    cached = _cache_get("quote_cache", "symbol", key, settings.quote_cache_ttl)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        quote = await _try_providers(lambda p: p.quote(key), f"quote:{key}")
    except ProviderError:
        stale = _cache_get_stale("quote_cache", "symbol", key)
        if stale is not None:
            return {**stale, "cached": True, "stale": True}
        raise

    _cache_put("quote_cache", "symbol", key, quote)
    return {**quote, "cached": False}


async def get_overview(symbol: str) -> Dict[str, Any]:
    key = symbol.strip().upper()
    cache_key = f"overview:{key}"

    cached = _cache_get("quote_cache", "symbol", cache_key, settings.overview_cache_ttl)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        overview = await _try_providers(lambda p: p.overview(key), f"overview:{key}")
    except ProviderError:
        stale = _cache_get_stale("quote_cache", "symbol", cache_key)
        if stale is not None:
            return {**stale, "cached": True, "stale": True}
        raise

    _cache_put("quote_cache", "symbol", cache_key, overview)
    return {**overview, "cached": False}


def _sma(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    """Simple moving average, returned index-aligned with `values`.

    Entries before the window is full are None rather than a partial average,
    so a 200-day line does not start with a meaningless 3-day mean.
    """
    out: List[Optional[float]] = []
    running = 0.0
    buf: List[float] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        buf.append(v)
        running += v
        if len(buf) > window:
            running -= buf.pop(0)
        out.append(running / window if len(buf) == window else None)
    return out


async def get_history(symbol: str, range_: str = "1y") -> Dict[str, Any]:
    """Price history plus moving averages, cached per symbol+range.

    The TTL is short for intraday-relevant ranges and long for multi-year
    ones: a 10-year monthly series does not change during the day.
    """
    key = symbol.strip().upper()
    if not key:
        raise ProviderError("Symbol is required")

    cache_key = f"history:{key}:{range_}"
    ttl = 900 if range_ in ("1m", "6m", "1y") else 86400

    cached = _cache_get("quote_cache", "symbol", cache_key, ttl)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        data = await _try_providers(
            lambda p: p.history(key, range_), f"history:{key}:{range_}"
        )
    except ProviderError:
        stale = _cache_get_stale("quote_cache", "symbol", cache_key)
        if stale is not None:
            return {**stale, "cached": True}
        raise

    closes = [c.get("c") for c in data.get("candles", [])]
    data["sma_50"] = _sma(closes, 50)
    data["sma_200"] = _sma(closes, 200)
    data["currency_symbol"] = currency_symbol(data.get("currency"))

    _cache_put("quote_cache", "symbol", cache_key, data)
    return {**data, "cached": False}
