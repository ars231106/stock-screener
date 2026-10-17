"""Refresh the `fundamentals` table from the market data provider chain.

Run on a schedule (GitHub Actions by default) rather than inside the API
server, for two reasons:

1. Yahoo refuses its fundamentals endpoint from some datacenter IP ranges,
   Render's included. The API server literally cannot fetch this data.
2. Even where it can, fetching fundamentals per request makes screening cost
   O(universe) upstream calls. Precomputing makes a screen one SQL query.

Usage:
    python -m jobs.refresh_fundamentals            # refresh stale rows
    python -m jobs.refresh_fundamentals --all      # refresh everything
    python -m jobs.refresh_fundamentals --seed     # seed universe first
    python -m jobs.refresh_fundamentals --limit 20 # cap the batch

Exit codes: 0 if at least one row was written, 1 if every symbol failed --
so a scheduled run that silently stops working shows up as a red build.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

# Allow `python jobs/refresh_fundamentals.py` as well as `-m`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.supabase_client import require_supabase  # noqa: E402
from app.data.universe import seed_rows  # noqa: E402
from app.providers.base import ProviderError, RateLimitError  # noqa: E402
from app.services import market_data  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
log = logging.getLogger("refresh")

# Columns the fundamentals table accepts. Anything else the provider returns
# (fetched_at, cached flags) is dropped rather than failing the insert.
COLUMNS = {
    "symbol", "name", "exchange", "currency", "country", "sector", "industry",
    "description", "market_cap", "pe_ratio", "peg_ratio", "pb_ratio", "eps",
    "book_value", "dividend_yield", "dividend_per_share", "profit_margin",
    "operating_margin", "roe", "roa", "revenue_ttm", "revenue_growth_yoy",
    "earnings_growth_yoy", "beta", "week_52_high", "week_52_low",
}


def seed_universe() -> int:
    sb = require_supabase()
    rows = seed_rows()
    sb.table("universe").upsert(rows, on_conflict="symbol").execute()
    log.info("seeded %d universe rows", len(rows))
    return len(rows)


def symbols_to_refresh(refresh_all: bool, max_age_hours: int, limit: int | None) -> list[str]:
    sb = require_supabase()
    universe = (
        sb.table("universe").select("symbol").eq("active", True).execute().data or []
    )
    all_symbols = [r["symbol"] for r in universe]
    if refresh_all:
        return all_symbols[:limit] if limit else all_symbols

    existing = sb.table("fundamentals").select("symbol, updated_at").execute().data or []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    fresh = set()
    for row in existing:
        try:
            ts = datetime.fromisoformat(str(row["updated_at"]).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts > cutoff:
                fresh.add(row["symbol"])
        except (ValueError, TypeError, KeyError):
            continue

    stale = [s for s in all_symbols if s not in fresh]
    return stale[:limit] if limit else stale


async def fetch_one(symbol: str, sem: asyncio.Semaphore) -> dict[str, Any] | None:
    async with sem:
        try:
            overview = await market_data.get_overview(symbol)
        except RateLimitError as exc:
            log.warning("%s: rate limited (%s)", symbol, exc)
            return None
        except ProviderError as exc:
            log.warning("%s: %s", symbol, exc)
            return None
        except Exception:
            log.exception("%s: unexpected failure", symbol)
            return None

    row = {k: v for k, v in overview.items() if k in COLUMNS}
    row["symbol"] = symbol
    # A row with no usable metric is noise -- skip rather than storing nulls
    # that would make the symbol look covered when it is not.
    if not any(
        row.get(k) is not None
        for k in ("pe_ratio", "pb_ratio", "roe", "market_cap", "profit_margin")
    ):
        log.warning("%s: no usable metrics, skipping", symbol)
        return None
    row["source"] = "provider-chain"
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    return row


async def run(args: argparse.Namespace) -> int:
    if args.seed:
        seed_universe()

    symbols = symbols_to_refresh(args.all, args.max_age_hours, args.limit)
    if not symbols:
        log.info("nothing to refresh -- every symbol is fresh")
        return 0

    log.info("refreshing %d symbols with concurrency %d", len(symbols), args.concurrency)
    sem = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*(fetch_one(s, sem) for s in symbols))
    rows = [r for r in results if r]

    if not rows:
        log.error("every symbol failed -- provider may be blocking this host")
        return 1

    sb = require_supabase()
    # Chunked so one oversized request cannot fail the whole run.
    written = 0
    for i in range(0, len(rows), 50):
        chunk = rows[i : i + 50]
        sb.table("fundamentals").upsert(chunk, on_conflict="symbol").execute()
        written += len(chunk)
        log.info("wrote %d/%d", written, len(rows))

    failed = len(symbols) - len(rows)
    log.info("done: %d written, %d failed", written, failed)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Refresh the fundamentals table")
    p.add_argument("--all", action="store_true", help="refresh every symbol, not just stale ones")
    p.add_argument("--seed", action="store_true", help="upsert the default universe first")
    p.add_argument("--limit", type=int, default=None, help="cap how many symbols to refresh")
    p.add_argument("--max-age-hours", type=int, default=20, dest="max_age_hours")
    p.add_argument("--concurrency", type=int, default=4)
    args = p.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
