"""The screening engine.

A screen is a list of criteria -- {metric, op, value} -- combined with AND
semantics. A company missing a required metric is excluded rather than
assumed to pass, which is the behaviour you want: an unknown P/E is not a
low P/E.

Criteria are translated into SQL predicates against the `fundamentals`
table, so one screen is one indexed query regardless of universe size. The
previous implementation fetched fundamentals per symbol from the market data
provider on every request -- O(universe) upstream calls, which neither the
provider's rate limits nor the response budget could sustain, and which is
impossible from a host whose IP the provider blocks.

The table is populated out of band by jobs/refresh_fundamentals.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.supabase_client import get_supabase
from app.services import market_data
from app.services.market_data import MarketDataError

log = logging.getLogger(__name__)

# Screenable metrics. The key is both the API contract and the column name.
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

SELECT_COLUMNS = "symbol, name, sector, currency, " + ", ".join(METRICS)

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

# Criterion operator -> PostgREST filter operator.
_PG_OP = {"gt": "gt", "gte": "gte", "lt": "lt", "lte": "lte", "eq": "eq"}


def _apply(query, criterion: Dict[str, Any]):
    """Translate one criterion into a PostgREST predicate.

    `not_("col", "is", "null")` is what enforces exclude-on-missing: without
    it a null would simply not match the comparison, which happens to give
    the right answer for most operators but not for `between`, and relying on
    that would be accidental rather than intended.
    """
    metric = criterion.get("metric")
    if metric not in METRICS:
        raise ValueError(f"Unknown metric: {metric}")

    op = criterion.get("op", "gt")
    value = criterion.get("value")
    query = query.not_.is_(metric, "null")

    if op == "between":
        upper = criterion.get("value2")
        if upper is None:
            raise ValueError("'between' needs both value and value2")
        lo, hi = sorted((float(value), float(upper)))
        return query.gte(metric, lo).lte(metric, hi)

    pg_op = _PG_OP.get(op)
    if pg_op is None:
        raise ValueError(f"Unknown operator: {op}")
    return getattr(query, pg_op)(metric, value)


async def run_screen(
    criteria: List[Dict[str, Any]],
    symbols: Optional[List[str]] = None,
    limit: int = 25,
    market: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate `criteria` against the stored fundamentals."""
    sb = get_supabase()
    if sb is None:
        return {
            "criteria": criteria, "evaluated": 0, "matched": 0, "partial": True,
            "message": "The database is not configured.", "results": [],
        }

    try:
        total = (
            sb.table("fundamentals").select("symbol", count="exact")
            .limit(1).execute().count or 0
        )
    except Exception as exc:
        log.warning("could not count fundamentals: %s", exc)
        total = 0

    if total == 0:
        return {
            "criteria": criteria, "evaluated": 0, "matched": 0, "partial": True,
            "message": (
                "No fundamentals have been loaded yet. The refresh job "
                "populates them on a schedule."
            ),
            "results": [],
        }

    query = sb.table("fundamentals").select(SELECT_COLUMNS)
    try:
        for criterion in criteria:
            query = _apply(query, criterion)
    except ValueError as exc:
        return {
            "criteria": criteria, "evaluated": total, "matched": 0,
            "partial": False, "message": str(exc), "results": [],
        }

    if symbols:
        query = query.in_("symbol", [s.strip().upper() for s in symbols if s.strip()])
    if market:
        universe = (
            sb.table("universe").select("symbol").eq("market", market.upper())
            .eq("active", True).execute().data or []
        )
        query = query.in_("symbol", [r["symbol"] for r in universe])

    try:
        rows = query.limit(max(1, min(limit, 200))).execute().data or []
    except Exception as exc:
        log.exception("screen query failed")
        return {
            "criteria": criteria, "evaluated": total, "matched": 0,
            "partial": True, "message": f"Screen failed: {exc}", "results": [],
        }

    metrics_used = [c["metric"] for c in criteria if c.get("metric") in METRICS]
    results = []
    for row in rows:
        # Quotes are cheap and cached; a failure here must not drop the row.
        price = None
        change_percent = None
        try:
            quote = await market_data.get_quote(row["symbol"])
            price = quote.get("price")
            change_percent = quote.get("change_percent")
        except MarketDataError:
            pass

        results.append(
            {
                "symbol": row["symbol"],
                "name": row.get("name"),
                "sector": row.get("sector"),
                "price": price,
                "change_percent": change_percent,
                "metrics": {m: row.get(m) for m in metrics_used},
                "passed": True,
            }
        )

    results.sort(key=lambda r: r["symbol"])
    return {
        "criteria": criteria,
        "evaluated": total,
        "matched": len(results),
        "partial": False,
        "message": None,
        "results": results,
    }


def universe_size() -> int:
    sb = get_supabase()
    if sb is None:
        return 0
    try:
        return (
            sb.table("fundamentals").select("symbol", count="exact")
            .limit(1).execute().count or 0
        )
    except Exception:
        return 0


def coverage() -> Dict[str, Any]:
    """How complete and how fresh the fundamentals table is."""
    sb = get_supabase()
    if sb is None:
        return {"symbols": 0, "oldest_update": None}
    try:
        rows = (
            sb.table("fundamentals").select("updated_at")
            .order("updated_at", desc=False).limit(1).execute().data or []
        )
        count = (
            sb.table("fundamentals").select("symbol", count="exact")
            .limit(1).execute().count or 0
        )
        return {
            "symbols": count,
            "oldest_update": rows[0]["updated_at"] if rows else None,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return {"symbols": 0, "oldest_update": None}
