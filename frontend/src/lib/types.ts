export interface SymbolMatch {
  symbol: string;
  name?: string | null;
  type?: string | null;
  region?: string | null;
  currency?: string | null;
  match_score: number;
}

export interface SearchResponse {
  query: string;
  matches: SymbolMatch[];
}

export interface Quote {
  symbol: string;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  price?: number | null;
  volume: number;
  latest_trading_day?: string | null;
  previous_close?: number | null;
  change?: number | null;
  change_percent: string;
  fetched_at?: string | null;
  cached: boolean;
  stale: boolean;
}

export interface Overview {
  symbol: string;
  name?: string | null;
  description?: string | null;
  exchange?: string | null;
  currency?: string | null;
  country?: string | null;
  sector?: string | null;
  industry?: string | null;
  market_cap?: number | null;
  pe_ratio?: number | null;
  peg_ratio?: number | null;
  pb_ratio?: number | null;
  eps?: number | null;
  book_value?: number | null;
  dividend_yield?: number | null;
  dividend_per_share?: number | null;
  profit_margin?: number | null;
  operating_margin?: number | null;
  roe?: number | null;
  roa?: number | null;
  revenue_ttm?: number | null;
  revenue_growth_yoy?: number | null;
  earnings_growth_yoy?: number | null;
  beta?: number | null;
  week_52_high?: number | null;
  week_52_low?: number | null;
}

export interface StockDetail {
  symbol: string;
  name?: string | null;
  region?: string | null;
  currency?: string | null;
  currency_symbol: string;
  quote?: Quote | null;
  overview?: Overview | null;
  in_watchlist: boolean;
}

export interface WatchlistItem {
  id: string;
  watchlist_id: string;
  symbol: string;
  company_name?: string | null;
  region?: string | null;
  currency?: string | null;
  notes?: string | null;
  added_at: string;
  quote?: Quote | null;
}

export type Operator = "gt" | "gte" | "lt" | "lte" | "eq" | "between";

export interface Criterion {
  metric: string;
  op: Operator;
  value: number;
  value2?: number | null;
}

export interface MetricMeta {
  key: string;
  label: string;
  unit: string;
}

export interface MetricsResponse {
  metrics: MetricMeta[];
  operators: { key: Operator; label: string }[];
  universe_size: number;
}

export interface Preset {
  key: string;
  name: string;
  description: string;
  criteria: Criterion[];
}

export interface ScreenResultRow {
  symbol: string;
  name?: string | null;
  sector?: string | null;
  price?: number | null;
  change_percent?: string | null;
  metrics: Record<string, number | null>;
  passed: boolean;
}

export interface ScreenRunResponse {
  criteria: Criterion[];
  evaluated: number;
  /** Total companies passing the criteria. */
  matched: number;
  /** How many of them are in `results` (the page). */
  returned?: number;
  truncated?: boolean;
  partial: boolean;
  message?: string | null;
  results: ScreenResultRow[];
}

export interface SavedScreen {
  id: string;
  name: string;
  description?: string | null;
  criteria: Criterion[];
  is_public: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface SearchHistoryEntry {
  id: string;
  query: string;
  symbol?: string | null;
  company_name?: string | null;
  searched_at: string;
}

export interface Profile {
  id: string;
  username?: string | null;
  display_name?: string | null;
  avatar_url?: string | null;
  created_at?: string | null;
}

export type HistoryRange = "1m" | "6m" | "1y" | "3y" | "5y" | "10y" | "max";

export interface Candle {
  t: string;
  o?: number | null;
  h?: number | null;
  l?: number | null;
  c?: number | null;
  v: number;
}

export interface PriceHistory {
  symbol: string;
  currency?: string | null;
  currency_symbol: string;
  range: string;
  interval: string;
  candles: Candle[];
  sma_50: (number | null)[];
  sma_200: (number | null)[];
  cached: boolean;
}
