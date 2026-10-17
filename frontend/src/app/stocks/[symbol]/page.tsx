"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import PriceChart from "@/components/PriceChart";
import SearchBar from "@/components/SearchBar";
import { api, ApiError } from "@/lib/api";
import {
  changeTone,
  compact,
  metricValue,
  money,
  percent,
  ratio,
  timeAgo,
  volume,
} from "@/lib/format";
import type { StockDetail } from "@/lib/types";

const REFRESH_MS = 60_000;

const FUNDAMENTALS: { key: keyof NonNullable<StockDetail["overview"]>; label: string; unit: string }[] =
  [
    { key: "market_cap", label: "Market Cap", unit: "abs" },
    { key: "pe_ratio", label: "P/E Ratio", unit: "x" },
    { key: "pb_ratio", label: "P/B Ratio", unit: "x" },
    { key: "peg_ratio", label: "PEG Ratio", unit: "x" },
    { key: "eps", label: "EPS", unit: "" },
    { key: "book_value", label: "Book Value", unit: "" },
    { key: "dividend_yield", label: "Dividend Yield", unit: "pct" },
    { key: "roe", label: "Return on Equity", unit: "pct" },
    { key: "roa", label: "Return on Assets", unit: "pct" },
    { key: "profit_margin", label: "Profit Margin", unit: "pct" },
    { key: "operating_margin", label: "Operating Margin", unit: "pct" },
    { key: "revenue_growth_yoy", label: "Revenue Growth YoY", unit: "pct" },
    { key: "earnings_growth_yoy", label: "Earnings Growth YoY", unit: "pct" },
    { key: "beta", label: "Beta", unit: "" },
  ];

export default function StockPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = decodeURIComponent(
    Array.isArray(params.symbol) ? params.symbol[0] : params.symbol
  ).toUpperCase();

  const { user } = useAuth();
  const [data, setData] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchBusy, setWatchBusy] = useState(false);

  const load = useCallback(
    async (isRefresh = false) => {
      isRefresh ? setRefreshing(true) : setLoading(true);
      try {
        const res = await api.stock(symbol);
        setData(res);
        setError(null);
      } catch (err) {
        // A failed background refresh should not blank a page that is
        // already showing good data.
        const message =
          err instanceof ApiError ? err.message : "Could not load this stock.";
        if (!isRefresh) setError(message);
      } finally {
        isRefresh ? setRefreshing(false) : setLoading(false);
      }
    },
    [symbol]
  );

  useEffect(() => {
    load();
  }, [load]);

  // Poll while the tab is visible. The backend caches, so this is cheap.
  useEffect(() => {
    const id = setInterval(() => {
      if (document.visibilityState === "visible") load(true);
    }, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  async function toggleWatchlist() {
    if (!data) return;
    setWatchBusy(true);
    try {
      if (data.in_watchlist) {
        await api.removeFromWatchlist(symbol);
        setData({ ...data, in_watchlist: false });
      } else {
        await api.addToWatchlist({
          symbol,
          company_name: data.name,
          region: data.region,
          currency: data.currency,
        });
        setData({ ...data, in_watchlist: true });
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not update the watchlist."
      );
    } finally {
      setWatchBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="card animate-pulse space-y-4">
          <div className="h-7 w-2/3 rounded bg-slate-200 dark:bg-slate-800" />
          <div className="h-12 w-1/3 rounded bg-slate-200 dark:bg-slate-800" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="h-16 rounded bg-slate-200 dark:bg-slate-800"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center sm:px-6">
        <h1 className="section-title">{symbol}</h1>
        <div className="card mt-6 border-amber-300 bg-amber-50 text-left dark:border-amber-800 dark:bg-amber-950/30">
          <p className="text-sm text-amber-700 dark:text-amber-300">{error}</p>
        </div>
        <div className="mt-8">
          <SearchBar size="sm" placeholder="Try another company…" />
        </div>
        <Link href="/" className="btn-ghost mt-6 inline-flex">
          ← Back home
        </Link>
      </div>
    );
  }

  if (!data) return null;

  const q = data.quote;
  const cs = data.currency_symbol;
  const tone = changeTone(q?.change);
  const toneClass =
    tone === "up"
      ? "text-ticker-up"
      : tone === "down"
      ? "text-ticker-down"
      : "text-slate-500";

  const range52 =
    data.overview?.week_52_low != null && data.overview?.week_52_high != null
      ? `${money(data.overview.week_52_low, cs)} – ${money(
          data.overview.week_52_high,
          cs
        )}`
      : "—";

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8">
        <SearchBar size="sm" placeholder="Search another company…" />
      </div>

      {/* ---------------- price card ---------------- */}
      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100 sm:text-2xl">
              {data.name || symbol}
            </h1>
            <p className="muted mt-1">
              {symbol}
              {data.overview?.exchange ? ` · ${data.overview.exchange}` : ""}
              {data.region ? ` · ${data.region}` : ""}
              {data.overview?.sector ? ` · ${data.overview.sector}` : ""}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {user ? (
              <button
                type="button"
                onClick={toggleWatchlist}
                disabled={watchBusy}
                className={
                  data.in_watchlist ? "btn-secondary" : "btn-primary"
                }
              >
                {watchBusy
                  ? "…"
                  : data.in_watchlist
                  ? "★ In watchlist"
                  : "☆ Add to watchlist"}
              </button>
            ) : (
              <Link href="/login" className="btn-secondary">
                Log in to track
              </Link>
            )}
            <button
              type="button"
              onClick={() => load(true)}
              disabled={refreshing}
              className="btn-ghost"
            >
              {refreshing ? "Refreshing…" : "↻ Refresh"}
            </button>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-baseline gap-4">
          <span className="text-4xl font-semibold text-slate-900 dark:text-slate-50">
            {money(q?.price, cs)}
          </span>
          <span className={`text-lg font-semibold ${toneClass}`}>
            {q?.change != null && q.change >= 0 ? "+" : ""}
            {ratio(q?.change)}{" "}
            {q?.change_percent ? `(${q.change_percent})` : ""}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <Stat label="Open" value={money(q?.open, cs)} />
          <Stat label="High" value={money(q?.high, cs)} />
          <Stat label="Low" value={money(q?.low, cs)} />
          <Stat label="Prev. close" value={money(q?.previous_close, cs)} />
          <Stat label="Volume" value={volume(q?.volume)} />
          <Stat label="52-week range" value={range52} />
        </div>

        <p className="muted mt-6 flex flex-wrap items-center gap-2 text-xs">
          <span>
            Updated {timeAgo(q?.fetched_at) || "just now"}
            {q?.latest_trading_day ? ` · trading day ${q.latest_trading_day}` : ""}
          </span>
          {q?.cached && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
              served from cache
            </span>
          )}
          {q?.stale && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
              provider rate-limited — showing last known data
            </span>
          )}
        </p>
      </div>

      {/* ---------------- price chart ---------------- */}
      <PriceChart symbol={symbol} currencySymbol={cs} />

      {/* ---------------- fundamentals ---------------- */}
      {data.overview ? (
        <div className="card mt-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Fundamentals
          </h2>
          <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {FUNDAMENTALS.map((f) => (
              <Stat
                key={f.key as string}
                label={f.label}
                value={metricValue(
                  data.overview?.[f.key] as number | null | undefined,
                  f.unit
                )}
              />
            ))}
          </div>

          {data.overview.description && (
            <>
              <h3 className="mt-8 text-sm font-semibold text-slate-800 dark:text-slate-200">
                About {data.overview.name}
              </h3>
              <p className="muted mt-2 leading-relaxed">
                {data.overview.description}
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="card mt-6">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Fundamentals
          </h2>
          <p className="muted mt-2">
            No fundamentals are published for this ticker. Coverage is best for
            US-listed companies; Indian listings usually return price data only.
          </p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </p>
    </div>
  );
}
