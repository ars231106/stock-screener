"""Provider-agnostic contract for market data.

The application talks to this interface, never to a vendor SDK directly.
Swapping Yahoo for Alpha Vantage, or adding a third source, means adding a
module here -- no change to the routers, the screening engine or the cache.

Every provider returns the same normalised dictionaries, so the response
schemas are stable regardless of which upstream answered.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable


class ProviderError(Exception):
    """Upstream data could not be obtained."""


class RateLimitError(ProviderError):
    """Upstream refused because of its rate limit."""


class NotSupportedError(ProviderError):
    """This provider cannot answer this kind of request."""


@runtime_checkable
class MarketDataProvider(Protocol):
    """What every data source must be able to do.

    Implementations are async and must raise ProviderError (or the more
    specific RateLimitError) rather than returning partial data, so the
    caller can decide whether to fall back or serve a stale cache entry.
    """

    name: str

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Companies matching a name or ticker fragment."""
        ...

    async def quote(self, symbol: str) -> Dict[str, Any]:
        """Latest price snapshot for one ticker."""
        ...

    async def overview(self, symbol: str) -> Dict[str, Any]:
        """Company fundamentals for one ticker."""
        ...


# --------------------------------------------------------------------------
# Normalisation helpers shared by every provider
# --------------------------------------------------------------------------
def to_float(value: Any) -> float | None:
    """Coerce a provider's loose numeric field to a float, or None."""
    if value in (None, "None", "-", "", "N/A"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    # Providers occasionally return NaN for a missing figure.
    return None if result != result else result


def to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


SEARCH_FIELDS = ("symbol", "name", "type", "region", "currency", "match_score")

QUOTE_FIELDS = (
    "symbol", "open", "high", "low", "price", "volume", "latest_trading_day",
    "previous_close", "change", "change_percent",
)

OVERVIEW_FIELDS = (
    "symbol", "name", "description", "exchange", "currency", "country",
    "sector", "industry", "market_cap", "pe_ratio", "peg_ratio", "pb_ratio",
    "eps", "book_value", "dividend_yield", "dividend_per_share",
    "profit_margin", "operating_margin", "roe", "roa", "revenue_ttm",
    "revenue_growth_yoy", "earnings_growth_yoy", "beta", "week_52_high",
    "week_52_low",
)
