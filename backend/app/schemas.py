from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------- market data ---------------------------------
class SymbolMatch(BaseModel):
    symbol: str
    name: str | None = None
    type: str | None = None
    region: str | None = None
    currency: str | None = None
    match_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    matches: list[SymbolMatch] = []


class Quote(BaseModel):
    symbol: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    price: float | None = None
    volume: int = 0
    latest_trading_day: str | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: str = ""
    fetched_at: str | None = None
    cached: bool = False
    stale: bool = False


class Overview(BaseModel):
    symbol: str
    name: str | None = None
    description: str | None = None
    exchange: str | None = None
    currency: str | None = None
    country: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    peg_ratio: float | None = None
    pb_ratio: float | None = None
    eps: float | None = None
    book_value: float | None = None
    dividend_yield: float | None = None
    dividend_per_share: float | None = None
    profit_margin: float | None = None
    operating_margin: float | None = None
    roe: float | None = None
    roa: float | None = None
    revenue_ttm: float | None = None
    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    beta: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    cached: bool = False
    stale: bool = False


class StockDetail(BaseModel):
    symbol: str
    name: str | None = None
    region: str | None = None
    currency: str | None = None
    currency_symbol: str = ""
    quote: Quote | None = None
    overview: Overview | None = None
    in_watchlist: bool = False


# --------------------------- watchlist -----------------------------------
class WatchlistItemCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    company_name: str | None = None
    region: str | None = None
    currency: str | None = None
    notes: str | None = None


class WatchlistItem(BaseModel):
    id: str
    watchlist_id: str
    symbol: str
    company_name: str | None = None
    region: str | None = None
    currency: str | None = None
    notes: str | None = None
    added_at: datetime


class WatchlistItemWithQuote(WatchlistItem):
    quote: Quote | None = None


# --------------------------- screens -------------------------------------
Operator = Literal["gt", "gte", "lt", "lte", "eq", "between"]


class Criterion(BaseModel):
    metric: str
    op: Operator
    value: float
    value2: float | None = None  # upper bound for "between"


class SavedScreenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    criteria: list[Criterion] = []
    is_public: bool = False


class SavedScreen(BaseModel):
    id: str
    name: str
    description: str | None = None
    criteria: list[Any] = []
    is_public: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class ScreenRunRequest(BaseModel):
    criteria: list[Criterion] = []
    symbols: list[str] | None = None  # defaults to the built-in universe
    limit: int = 25


class ScreenResultRow(BaseModel):
    symbol: str
    name: str | None = None
    sector: str | None = None
    price: float | None = None
    change_percent: str | None = None
    metrics: dict = {}
    passed: bool = True


class ScreenRunResponse(BaseModel):
    criteria: list[Criterion] = []
    evaluated: int = 0
    matched: int = 0          # total passing the criteria
    returned: int = 0         # how many are in `results` (page size)
    truncated: bool = False   # matched > returned
    partial: bool = False
    message: str | None = None
    results: list[ScreenResultRow] = []


# --------------------------- history / profile ---------------------------
class SearchHistoryEntry(BaseModel):
    id: str
    query: str
    symbol: str | None = None
    company_name: str | None = None
    searched_at: datetime


class Profile(BaseModel):
    id: str
    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None


class ProfileUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=40)
    display_name: str | None = Field(default=None, max_length=80)


# --------------------------- price history -------------------------------
class Candle(BaseModel):
    t: str                      # ISO date
    o: float | None = None
    h: float | None = None
    l: float | None = None
    c: float | None = None
    v: int = 0


class PriceHistory(BaseModel):
    symbol: str
    currency: str | None = None
    currency_symbol: str = ""
    range: str
    interval: str
    candles: list[Candle] = []
    # Simple moving averages, aligned index-for-index with `candles`;
    # None until enough history exists to fill the window.
    sma_50: list[float | None] = []
    sma_200: list[float | None] = []
    cached: bool = False
