from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------- market data ---------------------------------
class SymbolMatch(BaseModel):
    symbol: str
    name: Optional[str] = None
    type: Optional[str] = None
    region: Optional[str] = None
    currency: Optional[str] = None
    match_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    matches: List[SymbolMatch] = []


class Quote(BaseModel):
    symbol: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    price: Optional[float] = None
    volume: int = 0
    latest_trading_day: Optional[str] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: str = ""
    fetched_at: Optional[str] = None
    cached: bool = False
    stale: bool = False


class Overview(BaseModel):
    symbol: str
    name: Optional[str] = None
    description: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps: Optional[float] = None
    book_value: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_per_share: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    revenue_ttm: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    earnings_growth_yoy: Optional[float] = None
    beta: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    cached: bool = False
    stale: bool = False


class StockDetail(BaseModel):
    symbol: str
    name: Optional[str] = None
    region: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: str = ""
    quote: Optional[Quote] = None
    overview: Optional[Overview] = None
    in_watchlist: bool = False


# --------------------------- watchlist -----------------------------------
class WatchlistItemCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    company_name: Optional[str] = None
    region: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None


class WatchlistItem(BaseModel):
    id: str
    watchlist_id: str
    symbol: str
    company_name: Optional[str] = None
    region: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    added_at: datetime


class WatchlistItemWithQuote(WatchlistItem):
    quote: Optional[Quote] = None


# --------------------------- screens -------------------------------------
Operator = Literal["gt", "gte", "lt", "lte", "eq", "between"]


class Criterion(BaseModel):
    metric: str
    op: Operator
    value: float
    value2: Optional[float] = None  # upper bound for "between"


class SavedScreenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    criteria: List[Criterion] = []
    is_public: bool = False


class SavedScreen(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    criteria: List[Any] = []
    is_public: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class ScreenRunRequest(BaseModel):
    criteria: List[Criterion] = []
    symbols: Optional[List[str]] = None  # defaults to the built-in universe
    limit: int = 25


class ScreenResultRow(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    price: Optional[float] = None
    change_percent: Optional[str] = None
    metrics: dict = {}
    passed: bool = True


class ScreenRunResponse(BaseModel):
    criteria: List[Criterion] = []
    evaluated: int = 0
    matched: int = 0          # total passing the criteria
    returned: int = 0         # how many are in `results` (page size)
    truncated: bool = False   # matched > returned
    partial: bool = False
    message: Optional[str] = None
    results: List[ScreenResultRow] = []


# --------------------------- history / profile ---------------------------
class SearchHistoryEntry(BaseModel):
    id: str
    query: str
    symbol: Optional[str] = None
    company_name: Optional[str] = None
    searched_at: datetime


class Profile(BaseModel):
    id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, max_length=40)
    display_name: Optional[str] = Field(default=None, max_length=80)


# --------------------------- price history -------------------------------
class Candle(BaseModel):
    t: str                      # ISO date
    o: Optional[float] = None
    h: Optional[float] = None
    l: Optional[float] = None
    c: Optional[float] = None
    v: int = 0


class PriceHistory(BaseModel):
    symbol: str
    currency: Optional[str] = None
    currency_symbol: str = ""
    range: str
    interval: str
    candles: List[Candle] = []
    # Simple moving averages, aligned index-for-index with `candles`;
    # None until enough history exists to fill the window.
    sma_50: List[Optional[float]] = []
    sma_200: List[Optional[float]] = []
    cached: bool = False
