"""Shared fixtures.

The suite never touches Supabase or a market data provider. Both are
replaced with fakes, because a test that needs the network is a test that
fails for reasons unrelated to the code under test.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

# Set before any app module is imported: Settings reads the environment at
# import time, and a missing value would make the app behave as unconfigured.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-for-signing-only")
os.environ.setdefault("MARKET_DATA_PROVIDERS", "yahoo")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


class FakeResponse:
    def __init__(self, data: Any, count: int | None = None):
        self.data = data
        self.count = count


class FakeQuery:
    """Chainable stand-in for the Supabase query builder.

    Records the filters applied so tests can assert on the predicates a
    screen produced, rather than only on the rows it returned.
    """

    def __init__(self, table: FakeTable):
        self.table = table
        self.filters: list[tuple[str, str, Any]] = []
        self._limit: int | None = None
        self._count_mode: str | None = None
        self.not_ = self  # supports `.not_.is_(col, "null")`

    # -- filter verbs -----------------------------------------------------
    def eq(self, col: str, val: Any):
        self.filters.append(("eq", col, val))
        return self

    def gt(self, col: str, val: Any):
        self.filters.append(("gt", col, val))
        return self

    def gte(self, col: str, val: Any):
        self.filters.append(("gte", col, val))
        return self

    def lt(self, col: str, val: Any):
        self.filters.append(("lt", col, val))
        return self

    def lte(self, col: str, val: Any):
        self.filters.append(("lte", col, val))
        return self

    def in_(self, col: str, vals: Any):
        self.filters.append(("in", col, list(vals)))
        return self

    def is_(self, col: str, val: Any):
        self.filters.append(("not.is", col, val))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    # -- terminal ---------------------------------------------------------
    def execute(self):
        rows = self.table.rows_for(self)
        count = len(rows) if self._count_mode == "exact" else None
        if self._limit is not None:
            rows = rows[: self._limit]
        return FakeResponse(rows, count)


class FakeTable:
    def __init__(self, store: dict[str, list[dict]], name: str):
        self.store = store
        self.name = name
        self.last_upsert: list[dict] | None = None

    def select(self, *_cols, count: str | None = None):
        q = FakeQuery(self)
        q._count_mode = count
        return q

    def insert(self, payload):
        rows = payload if isinstance(payload, list) else [payload]
        self.store.setdefault(self.name, []).extend(rows)
        return FakeResponse(rows)

    def upsert(self, payload, on_conflict: str | None = None):
        rows = payload if isinstance(payload, list) else [payload]
        self.last_upsert = rows
        bucket = self.store.setdefault(self.name, [])
        for row in rows:
            key = on_conflict or "symbol"
            existing = next(
                (r for r in bucket if r.get(key) == row.get(key)), None
            )
            if existing:
                existing.update(row)
            else:
                bucket.append(dict(row))
        return FakeResponse(rows)

    def update(self, payload):
        q = FakeQuery(self)
        q.filters.append(("__update__", "", payload))
        return q

    def delete(self):
        return FakeQuery(self)

    def rows_for(self, query: FakeQuery) -> list[dict]:
        rows = list(self.store.get(self.name, []))
        for op, col, val in query.filters:
            if op == "eq":
                rows = [r for r in rows if r.get(col) == val]
            elif op == "gt":
                rows = [r for r in rows if _num(r.get(col)) is not None and r[col] > val]
            elif op == "gte":
                rows = [r for r in rows if _num(r.get(col)) is not None and r[col] >= val]
            elif op == "lt":
                rows = [r for r in rows if _num(r.get(col)) is not None and r[col] < val]
            elif op == "lte":
                rows = [r for r in rows if _num(r.get(col)) is not None and r[col] <= val]
            elif op == "in":
                rows = [r for r in rows if r.get(col) in val]
            elif op == "not.is":
                rows = [r for r in rows if r.get(col) is not None]
        return rows


def _num(v: Any) -> float | None:
    return v if isinstance(v, (int, float)) else None


class FakeSupabase:
    def __init__(self, store: dict[str, list[dict]] | None = None):
        self.store: dict[str, list[dict]] = store or {}
        self._tables: dict[str, FakeTable] = {}

    def table(self, name: str) -> FakeTable:
        if name not in self._tables:
            self._tables[name] = FakeTable(self.store, name)
        return self._tables[name]


@pytest.fixture
def fake_sb(monkeypatch):
    """Install a FakeSupabase everywhere the app reaches for a client."""
    sb = FakeSupabase()

    from app.core import supabase_client

    monkeypatch.setattr(supabase_client, "get_supabase", lambda: sb)
    monkeypatch.setattr(supabase_client, "require_supabase", lambda: sb)

    # Modules that imported the symbol directly need patching at their own
    # namespace, not just at the definition site.
    for mod in (
        "app.services.market_data",
        "app.services.screener",
        "app.services.fundamentals",
    ):
        try:
            import importlib

            m = importlib.import_module(mod)
            if hasattr(m, "get_supabase"):
                monkeypatch.setattr(m, "get_supabase", lambda: sb)
            if hasattr(m, "require_supabase"):
                monkeypatch.setattr(m, "require_supabase", lambda: sb)
        except ImportError:
            pass
    return sb


@pytest.fixture
def fundamentals_rows() -> list[dict]:
    """A small universe with the awkward cases deliberately included."""
    return [
        # ordinary profitable large cap
        dict(symbol="AAPL", name="Apple", sector="Technology", currency="USD",
             pe_ratio=39.4, pb_ratio=46.7, roe=1.49, profit_margin=0.276,
             operating_margin=0.326, dividend_yield=0.0031, market_cap=5.0e12,
             revenue_growth_yoy=0.164, earnings_growth_yoy=0.287, beta=1.07),
        # cheap on earnings and book, pays a dividend
        dict(symbol="BAC", name="Bank of America", sector="Financial Services",
             currency="USD", pe_ratio=12.2, pb_ratio=1.31, roe=0.107,
             profit_margin=0.281, operating_margin=0.313, dividend_yield=0.025,
             market_cap=3.6e11, revenue_growth_yoy=0.071,
             earnings_growth_yoy=-0.143, beta=1.21),
        # loss-making: P/E is absent, not zero
        dict(symbol="INTC", name="Intel", sector="Technology", currency="USD",
             pe_ratio=None, pb_ratio=5.18, roe=-0.107, profit_margin=-0.198,
             operating_margin=0.122, dividend_yield=0.0, market_cap=4.7e11,
             revenue_growth_yoy=0.254, earnings_growth_yoy=None, beta=2.23),
        # Indian listing with several metrics unpublished
        dict(symbol="ITC.NS", name="ITC", sector="Consumer Defensive",
             currency="INR", pe_ratio=16.6, pb_ratio=4.55, roe=None,
             profit_margin=0.259, operating_margin=0.249, dividend_yield=0.0607,
             market_cap=3.3e12, revenue_growth_yoy=-0.111,
             earnings_growth_yoy=-0.16, beta=-0.063),
    ]


@pytest.fixture
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def stale_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
