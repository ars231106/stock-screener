"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { HistoryRange, PriceHistory } from "@/lib/types";

const RANGES: { key: HistoryRange; label: string }[] = [
  { key: "1m", label: "1M" },
  { key: "6m", label: "6M" },
  { key: "1y", label: "1Y" },
  { key: "3y", label: "3Y" },
  { key: "5y", label: "5Y" },
  { key: "10y", label: "10Y" },
  { key: "max", label: "Max" },
];

// Layout. Heights are fixed; width is measured, because an SVG stretched with
// preserveAspectRatio would distort stroke widths and text.
const PRICE_H = 248;
const VOL_H = 54;
const GAP = 10;
const AXIS_H = 22;
const PAD_R = 54; // room for price labels on the right
const PAD_L = 6;
const TOTAL_H = PRICE_H + GAP + VOL_H + AXIS_H;

interface Props {
  symbol: string;
  currencySymbol?: string;
}

type SeriesKey = "sma50" | "sma200";

export default function PriceChart({ symbol, currencySymbol = "" }: Props) {
  const [range, setRange] = useState<HistoryRange>("1y");
  const [data, setData] = useState<PriceHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [shown, setShown] = useState<Record<SeriesKey, boolean>>({
    sma50: true,
    sma200: false,
  });
  const [hover, setHover] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);

  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setWidth(Math.max(280, entry.contentRect.width));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .priceHistory(symbol, range)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (!cancelled)
          setError(
            err instanceof ApiError ? err.message : "Could not load price history."
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, range]);

  const plotW = Math.max(40, width - PAD_L - PAD_R);

  const model = useMemo(() => {
    if (!data || data.candles.length === 0) return null;
    const candles = data.candles;
    const closes = candles.map((c) => c.c ?? 0);

    // The 200-period line is only meaningful once the window has filled; on a
    // 6-month range it never does, so the toggle is hidden rather than
    // offering a control that does nothing.
    const has50 = data.sma_50.some((v) => v != null);
    const has200 = data.sma_200.some((v) => v != null);

    const visible: (number | null)[][] = [closes];
    if (shown.sma50 && has50) visible.push(data.sma_50);
    if (shown.sma200 && has200) visible.push(data.sma_200);

    let lo = Infinity;
    let hi = -Infinity;
    for (const series of visible) {
      for (const v of series) {
        if (v == null) continue;
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) return null;
    if (lo === hi) {
      lo -= 1;
      hi += 1;
    }
    const padY = (hi - lo) * 0.08;
    lo -= padY;
    hi += padY;

    const maxVol = Math.max(...candles.map((c) => c.v || 0), 1);
    const n = candles.length;
    const x = (i: number) => PAD_L + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
    const y = (v: number) => PRICE_H - ((v - lo) / (hi - lo)) * PRICE_H;
    const vy = (v: number) => VOL_H - (v / maxVol) * VOL_H;

    const line = (series: (number | null)[]) => {
      let d = "";
      let pen = false;
      series.forEach((v, i) => {
        if (v == null) {
          pen = false;
          return;
        }
        d += `${pen ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)}`;
        pen = true;
      });
      return d;
    };

    const priceLine = line(closes);
    const area =
      priceLine +
      `L${x(n - 1).toFixed(2)},${PRICE_H}L${x(0).toFixed(2)},${PRICE_H}Z`;

    // Four gridlines, labelled on the right.
    const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);

    const first = closes[0];
    const last = closes[n - 1];
    const changePct = first ? ((last - first) / first) * 100 : 0;

    return {
      candles,
      closes,
      has50,
      has200,
      lo,
      hi,
      x,
      y,
      vy,
      line,
      priceLine,
      area,
      ticks,
      maxVol,
      changePct,
      first,
      last,
      n,
    };
  }, [data, shown, plotW]);

  const onMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!model) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const px = e.clientX - rect.left - PAD_L;
      const i = Math.round((px / plotW) * (model.n - 1));
      setHover(Math.min(model.n - 1, Math.max(0, i)));
    },
    [model, plotW]
  );

  const fmt = (v: number | null | undefined, dp = 2) =>
    v == null ? "—" : `${currencySymbol}${v.toLocaleString(undefined, {
      minimumFractionDigits: dp,
      maximumFractionDigits: dp,
    })}`;

  const fmtVol = (v: number) =>
    v >= 1e7
      ? `${(v / 1e7).toFixed(2)}Cr`
      : v >= 1e5
      ? `${(v / 1e5).toFixed(2)}L`
      : v.toLocaleString();

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });

  return (
    <div className="card mt-6">
      {/* ---- header: title + range filters in one row above the chart ---- */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Price history
          </h2>
          {model && (
            <p className="muted mt-0.5 text-xs">
              {fmt(model.first)} → {fmt(model.last)} ·{" "}
              <span
                className={
                  model.changePct >= 0 ? "text-ticker-up" : "text-ticker-down"
                }
              >
                {model.changePct >= 0 ? "+" : ""}
                {model.changePct.toFixed(2)}%
              </span>{" "}
              over {RANGES.find((r) => r.key === range)?.label}
            </p>
          )}
        </div>

        <div
          role="group"
          aria-label="Chart time range"
          className="flex flex-wrap gap-1"
        >
          {RANGES.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => setRange(r.key)}
              aria-pressed={range === r.key}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                range === r.key
                  ? "bg-brand text-white"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* ---------------------------- legend ---------------------------- */}
      {model && (
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
          <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
            <span
              className="inline-block h-0.5 w-4 rounded-full"
              style={{ background: "var(--chart-price)" }}
            />
            Close
          </span>
          {model.has50 && (
            <button
              type="button"
              onClick={() => setShown((s) => ({ ...s, sma50: !s.sma50 }))}
              aria-pressed={shown.sma50}
              className={`flex items-center gap-1.5 transition ${
                shown.sma50
                  ? "text-slate-600 dark:text-slate-300"
                  : "text-slate-400 line-through dark:text-slate-500"
              }`}
            >
              <span
                className="inline-block h-0.5 w-4 rounded-full"
                style={{ background: "var(--chart-sma50)" }}
              />
              50-period SMA
            </button>
          )}
          {model.has200 && (
            <button
              type="button"
              onClick={() => setShown((s) => ({ ...s, sma200: !s.sma200 }))}
              aria-pressed={shown.sma200}
              className={`flex items-center gap-1.5 transition ${
                shown.sma200
                  ? "text-slate-600 dark:text-slate-300"
                  : "text-slate-400 line-through dark:text-slate-500"
              }`}
            >
              <span
                className="inline-block h-0.5 w-4 rounded-full"
                style={{ background: "var(--chart-sma200)" }}
              />
              200-period SMA
            </button>
          )}
          <span className="muted ml-auto">
            {data?.interval === "1d"
              ? "daily"
              : data?.interval === "1wk"
              ? "weekly"
              : "monthly"}{" "}
            bars
          </span>
        </div>
      )}

      {/* ----------------------------- chart ----------------------------- */}
      <div ref={wrapRef} className="mt-3">
        {loading && (
          <div
            className="animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800"
            style={{ height: TOTAL_H }}
          />
        )}

        {!loading && error && (
          <div className="rounded-lg bg-amber-50 px-3 py-6 text-center text-sm text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
            {error}
          </div>
        )}

        {!loading && !error && !model && (
          <p className="muted py-10 text-center">
            No price history available for this ticker.
          </p>
        )}

        {!loading && !error && model && (
          <svg
            width={width}
            height={TOTAL_H}
            role="img"
            aria-label={`${symbol} price history over ${range}. ${fmt(
              model.first
            )} to ${fmt(model.last)}, ${model.changePct.toFixed(2)} percent.`}
            onMouseMove={onMove}
            onMouseLeave={() => setHover(null)}
            className="touch-none select-none"
          >
            <defs>
              <linearGradient id={`fill-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--chart-price)"
                  stopOpacity="0.22"
                />
                <stop
                  offset="100%"
                  stopColor="var(--chart-price)"
                  stopOpacity="0"
                />
              </linearGradient>
            </defs>

            {/* gridlines + right-hand price labels, recessive */}
            {model.ticks.map((t, i) => {
              const yy = model.y(t);
              return (
                <g key={i}>
                  <line
                    x1={PAD_L}
                    x2={PAD_L + plotW}
                    y1={yy}
                    y2={yy}
                    stroke="var(--chart-grid)"
                    strokeWidth="1"
                  />
                  <text
                    x={PAD_L + plotW + 6}
                    y={yy + 3.5}
                    fontSize="10"
                    fill="var(--chart-axis)"
                  >
                    {t >= 1000 ? Math.round(t).toLocaleString() : t.toFixed(1)}
                  </text>
                </g>
              );
            })}

            <path d={model.area} fill={`url(#fill-${symbol})`} />
            <path
              d={model.priceLine}
              fill="none"
              stroke="var(--chart-price)"
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {shown.sma50 && model.has50 && data && (
              <path
                d={model.line(data.sma_50)}
                fill="none"
                stroke="var(--chart-sma50)"
                strokeWidth="2"
                strokeLinejoin="round"
              />
            )}
            {shown.sma200 && model.has200 && data && (
              <path
                d={model.line(data.sma_200)}
                fill="none"
                stroke="var(--chart-sma200)"
                strokeWidth="2"
                strokeLinejoin="round"
              />
            )}

            {/* volume, its own panel sharing the x-axis -- never a second
                y-scale on the price plot */}
            <g transform={`translate(0, ${PRICE_H + GAP})`}>
              {model.candles.map((c, i) => {
                const bw = Math.max(1, plotW / model.n - 1);
                return (
                  <rect
                    key={i}
                    x={model.x(i) - bw / 2}
                    y={model.vy(c.v || 0)}
                    width={bw}
                    height={Math.max(0, VOL_H - model.vy(c.v || 0))}
                    fill="var(--chart-volume)"
                    opacity={hover === i ? 1 : 0.75}
                  />
                );
              })}
            </g>

            {/* x labels: first, middle, last only -- never one per point */}
            {[0, Math.floor(model.n / 2), model.n - 1].map((i, k) => (
              <text
                key={k}
                x={model.x(i)}
                y={TOTAL_H - 6}
                fontSize="10"
                fill="var(--chart-axis)"
                textAnchor={k === 0 ? "start" : k === 2 ? "end" : "middle"}
              >
                {new Date(model.candles[i].t).toLocaleDateString(undefined, {
                  month: "short",
                  year: "2-digit",
                })}
              </text>
            ))}

            {/* crosshair */}
            {hover != null && model.candles[hover] && (
              <g pointerEvents="none">
                <line
                  x1={model.x(hover)}
                  x2={model.x(hover)}
                  y1={0}
                  y2={PRICE_H + GAP + VOL_H}
                  stroke="var(--chart-crosshair)"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <circle
                  cx={model.x(hover)}
                  cy={model.y(model.closes[hover])}
                  r="4.5"
                  fill="var(--chart-price)"
                  stroke="var(--chart-surface)"
                  strokeWidth="2"
                />
              </g>
            )}
          </svg>
        )}
      </div>

      {/* ---------------------------- tooltip ---------------------------- */}
      {model && hover != null && model.candles[hover] && (
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 rounded-lg bg-slate-50 px-3 py-2 text-xs tabular-nums dark:bg-slate-800/60">
          <span className="font-medium text-slate-700 dark:text-slate-200">
            {fmtDate(model.candles[hover].t)}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            O {fmt(model.candles[hover].o)}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            H {fmt(model.candles[hover].h)}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            L {fmt(model.candles[hover].l)}
          </span>
          <span className="font-semibold text-slate-800 dark:text-slate-100">
            C {fmt(model.candles[hover].c)}
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            Vol {fmtVol(model.candles[hover].v)}
          </span>
          {shown.sma50 && data?.sma_50[hover] != null && (
            <span style={{ color: "var(--chart-sma50)" }}>
              50 {fmt(data.sma_50[hover])}
            </span>
          )}
          {shown.sma200 && data?.sma_200[hover] != null && (
            <span style={{ color: "var(--chart-sma200)" }}>
              200 {fmt(data.sma_200[hover])}
            </span>
          )}
        </div>
      )}

      {/* ------------------- table view (accessibility) ------------------- */}
      {model && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowTable((v) => !v)}
            className="text-xs font-medium text-brand hover:underline"
          >
            {showTable ? "Hide data table" : "View as table"}
          </button>
          {showTable && (
            <div className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="w-full text-xs tabular-nums">
                <caption className="sr-only">
                  {symbol} price history, {range}
                </caption>
                <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800">
                  <tr className="text-left text-slate-500 dark:text-slate-400">
                    <th className="px-3 py-2 font-medium">Date</th>
                    <th className="px-3 py-2 text-right font-medium">Close</th>
                    <th className="px-3 py-2 text-right font-medium">Volume</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {model.candles
                    .slice()
                    .reverse()
                    .map((c) => (
                      <tr key={c.t}>
                        <td className="px-3 py-1.5 text-slate-600 dark:text-slate-300">
                          {c.t}
                        </td>
                        <td className="px-3 py-1.5 text-right text-slate-800 dark:text-slate-100">
                          {fmt(c.c)}
                        </td>
                        <td className="px-3 py-1.5 text-right text-slate-500 dark:text-slate-400">
                          {fmtVol(c.v)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
