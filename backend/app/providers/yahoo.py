"""Yahoo Finance provider, via yfinance.

Chosen as the default because it has no API key, no daily request cap, and
-- unlike Alpha Vantage's free tier -- it publishes fundamentals for Indian
listings (RELIANCE.NS, TCS.NS and so on), which is what lets the screener
cover NSE as well as US markets.

The trade-off is that this is an unofficial endpoint: it can change without
notice and Yahoo throttles aggressively from shared cloud IPs. That is
exactly why it sits behind the provider interface with a fallback.

yfinance is synchronous and does blocking network I/O, so every call is
pushed to a worker thread to avoid stalling the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from app.providers.base import ProviderError, RateLimitError, to_float, to_int

log = logging.getLogger(__name__)

SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

# Yahoo rejects requests without a browser-like User-Agent.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Yahoo's exchange codes are terse; map the ones we care about to the
# region labels the UI already displays.
REGION_BY_SUFFIX = {
    "NS": "India/NSE",
    "BO": "India/BSE",
    "L": "United Kingdom",
    "TO": "Canada",
    "AX": "Australia",
    "HK": "Hong Kong",
    "T": "Japan",
    "DE": "Germany",
    "PA": "France",
    "SW": "Switzerland",
}


def _region_for(symbol: str, exchange: str | None) -> str:
    if "." in symbol:
        suffix = symbol.rsplit(".", 1)[-1].upper()
        if suffix in REGION_BY_SUFFIX:
            return REGION_BY_SUFFIX[suffix]
    return exchange or "United States"


class YahooProvider:
    name = "yahoo"

    # ---------------------------------------------------------------- search
    async def search(self, query: str) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=HEADERS) as client:
                resp = await client.get(
                    SEARCH_URL,
                    params={"q": query, "quotesCount": 12, "newsCount": 0},
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Yahoo search failed: {exc}") from exc

        if resp.status_code == 429:
            raise RateLimitError("Yahoo is throttling search requests")
        if resp.status_code != 200:
            raise ProviderError(f"Yahoo search returned HTTP {resp.status_code}")

        try:
            payload = resp.json()
        except ValueError as exc:
            raise ProviderError("Yahoo search returned a non-JSON response") from exc

        matches: List[Dict[str, Any]] = []
        for i, q in enumerate(payload.get("quotes", [])):
            symbol = q.get("symbol")
            # Equities and funds only -- futures and options are noise here.
            if not symbol or q.get("quoteType") not in ("EQUITY", "ETF", "MUTUALFUND"):
                continue
            matches.append(
                {
                    "symbol": symbol,
                    "name": q.get("shortname") or q.get("longname"),
                    "type": (q.get("quoteType") or "").title(),
                    "region": _region_for(symbol, q.get("exchDisp")),
                    "currency": None,  # not in the search payload; filled on detail
                    # Yahoo returns best-first; synthesise a descending score
                    # so the shape matches the other provider.
                    "match_score": round(max(0.0, 1.0 - i * 0.05), 4),
                }
            )
        return matches

    # ----------------------------------------------------------------- quote
    async def quote(self, symbol: str) -> Dict[str, Any]:
        def _fetch() -> Dict[str, Any]:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info

            def g(key: str):
                try:
                    return fast.get(key)
                except Exception:
                    return None

            price = to_float(g("lastPrice"))
            previous_close = to_float(g("previousClose"))

            if price is None and previous_close is None:
                raise ProviderError(f"No quote data available for {symbol}")

            change = None
            change_percent = ""
            if price is not None and previous_close:
                change = price - previous_close
                change_percent = f"{(change / previous_close) * 100:.4f}%"

            return {
                "symbol": symbol.upper(),
                "open": to_float(g("open")),
                "high": to_float(g("dayHigh")),
                "low": to_float(g("dayLow")),
                "price": price,
                "volume": to_int(g("lastVolume")),
                "latest_trading_day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent,
                "currency": g("currency"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        return await self._in_thread(_fetch, symbol)

    # -------------------------------------------------------------- overview
    async def overview(self, symbol: str) -> Dict[str, Any]:
        def _fetch() -> Dict[str, Any]:
            import yfinance as yf

            info = yf.Ticker(symbol).info or {}
            if not info.get("symbol") and not info.get("shortName"):
                raise ProviderError(f"No fundamentals available for {symbol}")

            # yfinance >= 1.x reports dividendYield in percent units
            # (Apple 0.32 = 0.32%, TCS 2.12 = 2.12%) while every other ratio
            # here is a decimal fraction. Always scale it down, so the
            # screener can compare it against the other ratios and the UI can
            # format all of them the same way. Do not make this conditional on
            # the value being > 1 -- that silently inflates low yields a
            # hundredfold.
            dividend_yield = to_float(info.get("dividendYield"))
            if dividend_yield is not None:
                dividend_yield = dividend_yield / 100

            return {
                "symbol": symbol.upper(),
                "name": info.get("shortName") or info.get("longName"),
                "description": info.get("longBusinessSummary"),
                "exchange": info.get("fullExchangeName") or info.get("exchange"),
                "currency": info.get("currency"),
                "country": info.get("country") or _region_for(symbol, None),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": to_float(info.get("marketCap")),
                "pe_ratio": to_float(info.get("trailingPE")),
                "peg_ratio": to_float(info.get("trailingPegRatio")),
                "pb_ratio": to_float(info.get("priceToBook")),
                "eps": to_float(info.get("trailingEps")),
                "book_value": to_float(info.get("bookValue")),
                "dividend_yield": dividend_yield,
                "dividend_per_share": to_float(info.get("dividendRate")),
                "profit_margin": to_float(info.get("profitMargins")),
                "operating_margin": to_float(info.get("operatingMargins")),
                "roe": to_float(info.get("returnOnEquity")),
                "roa": to_float(info.get("returnOnAssets")),
                "revenue_ttm": to_float(info.get("totalRevenue")),
                "revenue_growth_yoy": to_float(info.get("revenueGrowth")),
                "earnings_growth_yoy": to_float(info.get("earningsGrowth")),
                "beta": to_float(info.get("beta")),
                "week_52_high": to_float(info.get("fiftyTwoWeekHigh")),
                "week_52_low": to_float(info.get("fiftyTwoWeekLow")),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        return await self._in_thread(_fetch, symbol)

    # --------------------------------------------------------------- history
    # Range -> (yfinance period, interval). Longer ranges use coarser bars so
    # the payload stays small and the line stays readable: a 10-year daily
    # series is ~2500 points for maybe 900 pixels of width.
    RANGES = {
        "1m": ("1mo", "1d"),
        "6m": ("6mo", "1d"),
        "1y": ("1y", "1d"),
        "3y": ("3y", "1wk"),
        "5y": ("5y", "1wk"),
        "10y": ("10y", "1mo"),
        "max": ("max", "1mo"),
    }

    async def history(self, symbol: str, range_: str = "1y") -> Dict[str, Any]:
        period, interval = self.RANGES.get(range_, self.RANGES["1y"])

        def _fetch() -> Dict[str, Any]:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            # auto_adjust keeps splits/dividends from putting false cliffs in
            # the line -- without it a 1:5 split reads as an 80% crash.
            frame = ticker.history(period=period, interval=interval, auto_adjust=True)
            if frame is None or frame.empty:
                raise ProviderError(f"No price history available for {symbol}")

            currency = None
            try:
                currency = ticker.fast_info.get("currency")
            except Exception:
                pass

            candles = []
            for ts, row in frame.iterrows():
                def num(col):
                    v = row.get(col)
                    try:
                        f = float(v)
                    except (TypeError, ValueError):
                        return None
                    return None if f != f else f

                close = num("Close")
                if close is None:
                    continue  # a bar with no close cannot be plotted
                candles.append(
                    {
                        "t": ts.strftime("%Y-%m-%d"),
                        "o": num("Open"),
                        "h": num("High"),
                        "l": num("Low"),
                        "c": close,
                        "v": int(num("Volume") or 0),
                    }
                )

            if not candles:
                raise ProviderError(f"No usable price history for {symbol}")

            return {
                "symbol": symbol.upper(),
                "currency": currency,
                "range": range_,
                "interval": interval,
                "candles": candles,
            }

        return await self._in_thread(_fetch, symbol)

    # ----------------------------------------------------------------- utils
    @staticmethod
    async def _in_thread(fn, symbol: str) -> Dict[str, Any]:
        """Run a blocking yfinance call off the event loop.

        Yahoo signals throttling with a 429 buried inside yfinance's own
        exceptions, so the message is inspected to classify it -- a rate
        limit should trigger a fallback, a genuine miss should not.
        """
        try:
            return await asyncio.to_thread(fn)
        except ProviderError:
            raise
        except Exception as exc:
            text = str(exc).lower()
            if "429" in text or "too many requests" in text or "rate limit" in text:
                raise RateLimitError(f"Yahoo is throttling requests: {exc}") from exc
            raise ProviderError(f"Yahoo lookup failed for {symbol}: {exc}") from exc
