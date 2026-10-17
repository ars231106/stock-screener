"""Alpha Vantage provider.

Kept as a fallback rather than the default. Its free tier allows roughly 25
requests per day and the quota is partly shared across callers from the same
IP, which makes it unusable as a primary source from a cloud host -- but it
is a stable, documented API, so it is worth having behind the interface for
when Yahoo's unofficial endpoint misbehaves.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from app.providers.base import (
    NotSupportedError,
    ProviderError,
    RateLimitError,
    to_float,
    to_int,
)

log = logging.getLogger(__name__)


class AlphaVantageProvider:
    name = "alpha_vantage"

    def __init__(self, api_key: str, base_url: str = "https://www.alphavantage.co/query"):
        self.api_key = api_key
        self.base_url = base_url

    async def _call(self, params: Dict[str, str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ProviderError("Alpha Vantage key is not configured")

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                resp = await client.get(
                    self.base_url, params={**params, "apikey": self.api_key}
                )
            except httpx.HTTPError as exc:
                raise ProviderError(f"Alpha Vantage request failed: {exc}") from exc

        if resp.status_code != 200:
            raise ProviderError(f"Alpha Vantage returned HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderError("Alpha Vantage returned a non-JSON response") from exc

        # Throttling is signalled in the body with a 200 status code.
        if "Note" in data or "Information" in data:
            raise RateLimitError(data.get("Note") or data.get("Information", ""))
        if "Error Message" in data:
            raise ProviderError(data["Error Message"])
        return data

    async def search(self, query: str) -> List[Dict[str, Any]]:
        raw = await self._call({"function": "SYMBOL_SEARCH", "keywords": query})
        return [
            {
                "symbol": m.get("1. symbol"),
                "name": m.get("2. name"),
                "type": m.get("3. type"),
                "region": m.get("4. region"),
                "currency": m.get("8. currency"),
                "match_score": to_float(m.get("9. matchScore")) or 0.0,
            }
            for m in raw.get("bestMatches", [])
            if m.get("1. symbol")
        ]

    async def quote(self, symbol: str) -> Dict[str, Any]:
        raw = await self._call({"function": "GLOBAL_QUOTE", "symbol": symbol})
        q = raw.get("Global Quote") or {}
        if not q.get("01. symbol"):
            raise ProviderError(f"No quote data available for {symbol}")

        return {
            "symbol": q.get("01. symbol"),
            "open": to_float(q.get("02. open")),
            "high": to_float(q.get("03. high")),
            "low": to_float(q.get("04. low")),
            "price": to_float(q.get("05. price")),
            "volume": to_int(q.get("06. volume")),
            "latest_trading_day": q.get("07. latest trading day"),
            "previous_close": to_float(q.get("08. previous close")),
            "change": to_float(q.get("09. change")),
            "change_percent": (q.get("10. change percent") or "").strip(),
            "currency": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    async def overview(self, symbol: str) -> Dict[str, Any]:
        raw = await self._call({"function": "OVERVIEW", "symbol": symbol})
        if not raw or not raw.get("Symbol"):
            raise ProviderError(f"No fundamentals available for {symbol}")

        return {
            "symbol": raw.get("Symbol"),
            "name": raw.get("Name"),
            "description": raw.get("Description"),
            "exchange": raw.get("Exchange"),
            "currency": raw.get("Currency"),
            "country": raw.get("Country"),
            "sector": (raw.get("Sector") or "").title() or None,
            "industry": (raw.get("Industry") or "").title() or None,
            "market_cap": to_float(raw.get("MarketCapitalization")),
            "pe_ratio": to_float(raw.get("PERatio")),
            "peg_ratio": to_float(raw.get("PEGRatio")),
            "pb_ratio": to_float(raw.get("PriceToBookRatio")),
            "eps": to_float(raw.get("EPS")),
            "book_value": to_float(raw.get("BookValue")),
            "dividend_yield": to_float(raw.get("DividendYield")),
            "dividend_per_share": to_float(raw.get("DividendPerShare")),
            "profit_margin": to_float(raw.get("ProfitMargin")),
            "operating_margin": to_float(raw.get("OperatingMarginTTM")),
            "roe": to_float(raw.get("ReturnOnEquityTTM")),
            "roa": to_float(raw.get("ReturnOnAssetsTTM")),
            "revenue_ttm": to_float(raw.get("RevenueTTM")),
            "revenue_growth_yoy": to_float(raw.get("QuarterlyRevenueGrowthYOY")),
            "earnings_growth_yoy": to_float(raw.get("QuarterlyEarningsGrowthYOY")),
            "beta": to_float(raw.get("Beta")),
            "week_52_high": to_float(raw.get("52WeekHigh")),
            "week_52_low": to_float(raw.get("52WeekLow")),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    async def history(self, symbol: str, range_: str = "1y") -> Dict[str, Any]:
        # TIME_SERIES_DAILY_ADJUSTED is a premium endpoint on this provider,
        # so there is nothing useful to fall back to here. Raising the
        # specific error keeps the chain from retrying pointlessly.
        raise NotSupportedError(
            "Alpha Vantage's free tier does not serve adjusted price history"
        )
