"""The screening engine.

A screen is a list of criteria — ``{metric, op, value}`` — evaluated against
each stock's fundamentals. A stock passes only if it satisfies every
criterion (AND semantics), and any stock missing a required metric is
excluded rather than assumed to pass.

Note on the data source: Alpha Vantage has no bulk fundamentals endpoint on
the free tier, so a screen fetches ``OVERVIEW`` per symbol. That is slow and
rate-limited, which is exactly why ``market_data`` caches every overview in
Postgres for a day. The universe below is deliberately small for the same
reason; swap in a bulk provider and only ``UNIVERSE`` needs to change.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.services import market_data
from app.services.market_data import MarketDataError, RateLimitError

log = logging.getLogger(__name__)

# Metrics a criterion may reference, mapped to their key in the overview
# payload, with a human label and how the raw value should be read.
METRICS: Dict[str, Dict[str, Any]] = {
    "pe_ratio": {"label": "P/E Ratio", "unit": "x"},
    "peg_ratio": {"label": "PEG Ratio", "unit": "x"},
    "pb_ratio": {"label": "P/B Ratio", "unit": "x"},
    "eps": {"label": "EPS", "unit": ""},
    "market_cap": {"label": "Market Cap", "unit": "abs"},
    "dividend_yield": {"label": "Dividend Yield", "unit": "pct"},
    "profit_margin": {"label": "Profit Margin", "unit": "pct"},
    "operating_margin": {"label": "Operating Margin", "unit": "pct"},
    "roe": {"label": "Return on Equity", "unit": "pct"},
    "roa": {"label": "Return on Assets", "unit": "pct"},
    "revenue_growth_yoy": {"label": "Revenue Growth (YoY)", "unit": "pct"},
    "earnings_growth_yoy": {"label": "Earnings Growth (YoY)", "unit": "pct"},
    "beta": {"label": "Beta", "unit": ""},
}

# Default universe. US tickers because Alpha Vantage's free fundamentals
# coverage outside the US is thin; Indian tickers are searchable and
# quotable but rarely have an OVERVIEW payload.
UNIVERSE: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX",
    "AMD", "INTC", "JNJ", "JPM", "V", "MA", "WMT", "PG", "KO", "PEP",
    "XOM", "CVX", "DIS", "CSCO", "ORCL", "ADBE", "CRM", "PFE", "MRK",
    "T", "VZ", "IBM",
]

# The three presets the original UI advertised, now actually executable.
PRESET_SCREENS: Dict[str, Dict[str, Any]] = {
    "growth": {
        "name": "Growth Stocks",
        "description": "Above-average revenue and earnings growth with strong returns on equity.",
        "criteria": [
            {"metric": "revenue_growth_yoy", "op": "gt", "value": 0.10},
            {"metric": "earnings_growth_yoy", "op": "gt", "value": 0.10},
            {"metric": "roe", "op": "gt", "value": 0.15},
        ],
    },
    "value": {
        "name": "Value Stocks",
        "description": "Trading at modest multiples of earnings and book value.",
        "criteria": [
            {"metric": "pe_ratio", "op": "lt", "value": 20},
            {"metric": "pb_ratio", "op": "lt", "value": 4},
            {"metric": "dividend_yield", "op": "gt", "value": 0.01},
        ],
    },
    "dividend": {
        "name": "Dividend Stocks",
        "description": "Consistent payers with a healthy yield and profitable operations.",
        "criteria": [
            {"metric": "dividend_yield", "op": "gt", "value": 0.02},
            {"metric": "profit_margin", "op": "gt", "value": 0.05},
        ],
    },
    "quality": {
        "name": "Quality Compounders",
        "description": "High margins and high returns on capital, regardless of valuation.",
        "criteria": [
            {"metric": "roe", "op": "gt", "value": 0.20},
            {"metric": "operating_margin", "op": "gt", "value": 0.15},
            {"metric": "profit_margin", "op": "gt", "value": 0.10},
        ],
    },
}


def _compare(value: Optional[float], op: str, target: float,
             target2: Optional[float] = None) -> bool:
    if value is None:
        return False
    if op == "gt":
        return value > target
    if op == "gte":
        return value >= target
    if op == "lt":
        return value < target
    if op == "lte":
        return value <= target
    if op == "eq":
        return abs(value - target) < 1e-9
    if op == "between":
        if target2 is None:
            return False
        lo, hi = min(target, target2), max(target, target2)
        return lo <= value <= hi
    return False


def evaluate(overview: Dict[str, Any], criteria: List[Dict[str, Any]]) -> bool:
    """True only when every criterion is satisfied."""
    for c in criteria:
        metric = c.get("metric")
        if metric not in METRICS:
            return False
        if not _compare(
            overview.get(metric), c.get("op", "gt"), c.get("value", 0), c.get("value2")
        ):
            return False
    return True


async def run_screen(
    criteria: List[Dict[str, Any]],
    symbols: Optional[List[str]] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Evaluate ``criteria`` across a universe of tickers.

    Returns matched rows plus a ``partial`` flag: if the upstream provider
    throttles part-way through, we return what we managed to evaluate and
    say so, rather than failing the whole request.
    """
    universe = [s.strip().upper() for s in (symbols or UNIVERSE) if s and s.strip()]
    metrics_used = [c["metric"] for c in criteria if c.get("metric") in METRICS]

    evaluated = 0
    partial = False
    message: Optional[str] = None
    rows: List[Dict[str, Any]] = []

    # Modest concurrency — enough to be quick off the cache, gentle enough
    # not to trip the provider's per-minute limit on a cold cache.
    semaphore = asyncio.Semaphore(4)

    async def fetch(symbol: str):
        async with semaphore:
            try:
                return symbol, await market_data.get_overview(symbol), None
            except Exception as exc:
                return symbol, None, exc

    results = await asyncio.gather(*(fetch(s) for s in universe))

    for symbol, overview, error in results:
        if error is not None:
            if isinstance(error, RateLimitError):
                partial = True
                message = (
                    "Market data rate limit reached part-way through. "
                    "Showing results for the symbols already cached."
                )
            elif not isinstance(error, MarketDataError):
                log.warning("screen fetch failed for %s: %s", symbol, error)
            continue

        evaluated += 1
        if not evaluate(overview, criteria):
            continue

        price = None
        change_percent = None
        try:
            quote = await market_data.get_quote(symbol)
            price = quote.get("price")
            change_percent = quote.get("change_percent")
        except MarketDataError:
            pass

        rows.append(
            {
                "symbol": symbol,
                "name": overview.get("name"),
                "sector": overview.get("sector"),
                "price": price,
                "change_percent": change_percent,
                "metrics": {m: overview.get(m) for m in metrics_used},
                "passed": True,
            }
        )

    rows.sort(key=lambda r: r["symbol"])
    return {
        "criteria": criteria,
        "evaluated": evaluated,
        "matched": len(rows),
        "partial": partial,
        "message": message,
        "results": rows[:limit],
    }
