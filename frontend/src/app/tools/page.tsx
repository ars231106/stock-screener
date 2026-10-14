"use client";

import Link from "next/link";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { compact, metricValue, money, ratio } from "@/lib/format";
import type { StockDetail } from "@/lib/types";

type Tab = "returns" | "compare" | "sizing";

const TABS: { key: Tab; label: string; blurb: string }[] = [
  {
    key: "returns",
    label: "Return calculator",
    blurb: "Compound a lump sum and optional monthly contributions.",
  },
  {
    key: "compare",
    label: "Stock comparison",
    blurb: "Put two or three tickers side by side on the same metrics.",
  },
  {
    key: "sizing",
    label: "Position sizing",
    blurb: "Work out share count from your risk per trade and stop distance.",
  },
];

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("returns");

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="section-title">Investment tools</h1>
      <p className="muted mt-2">
        Small calculators for the arithmetic you would otherwise do in a
        spreadsheet.
      </p>

      <div className="mt-8 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
              tab === t.key
                ? "bg-brand text-white"
                : "border border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <p className="muted mt-3">{TABS.find((t) => t.key === tab)?.blurb}</p>

      <div className="mt-6">
        {tab === "returns" && <ReturnCalculator />}
        {tab === "compare" && <StockComparison />}
        {tab === "sizing" && <PositionSizing />}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
function ReturnCalculator() {
  const [initial, setInitial] = useState(100000);
  const [monthly, setMonthly] = useState(5000);
  const [rate, setRate] = useState(12);
  const [years, setYears] = useState(10);

  // Future value of a lump sum plus an ordinary annuity, compounded monthly.
  const months = Math.max(0, Math.round(years * 12));
  const r = rate / 100 / 12;
  const lumpFv = initial * Math.pow(1 + r, months);
  const contribFv =
    r === 0 ? monthly * months : monthly * ((Math.pow(1 + r, months) - 1) / r);
  const total = lumpFv + contribFv;
  const invested = initial + monthly * months;
  const gain = total - invested;

  return (
    <div className="card">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field
          label="Initial amount"
          value={initial}
          onChange={setInitial}
          min={0}
        />
        <Field
          label="Monthly contribution"
          value={monthly}
          onChange={setMonthly}
          min={0}
        />
        <Field
          label="Annual return (%)"
          value={rate}
          onChange={setRate}
          step={0.1}
        />
        <Field label="Years" value={years} onChange={setYears} min={0} step={1} />
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <Result label="Total invested" value={compact(invested)} />
        <Result label="Future value" value={compact(total)} highlight />
        <Result
          label="Gain"
          value={compact(gain)}
          tone={gain >= 0 ? "up" : "down"}
        />
      </div>

      <p className="muted mt-6 text-xs">
        Assumes a constant rate compounded monthly, contributions at the end of
        each month, and no taxes, fees or inflation. Real returns vary.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
function StockComparison() {
  const [inputs, setInputs] = useState<string[]>(["AAPL", "MSFT", ""]);
  const [rows, setRows] = useState<StockDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function compare() {
    const symbols = inputs.map((s) => s.trim().toUpperCase()).filter(Boolean);
    if (symbols.length < 2) {
      setError("Enter at least two tickers.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(symbols.map((s) => api.stock(s)));
      setRows(results);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not load those tickers."
      );
    } finally {
      setLoading(false);
    }
  }

  const METRICS: { key: string; label: string; unit: string }[] = [
    { key: "market_cap", label: "Market cap", unit: "abs" },
    { key: "pe_ratio", label: "P/E", unit: "x" },
    { key: "pb_ratio", label: "P/B", unit: "x" },
    { key: "eps", label: "EPS", unit: "" },
    { key: "dividend_yield", label: "Dividend yield", unit: "pct" },
    { key: "roe", label: "Return on equity", unit: "pct" },
    { key: "profit_margin", label: "Profit margin", unit: "pct" },
    { key: "revenue_growth_yoy", label: "Revenue growth YoY", unit: "pct" },
    { key: "beta", label: "Beta", unit: "" },
  ];

  return (
    <div className="card">
      <div className="grid gap-3 sm:grid-cols-4">
        {inputs.map((val, i) => (
          <div key={i}>
            <label className="label">Ticker {i + 1}</label>
            <input
              className="input uppercase"
              value={val}
              placeholder={i === 2 ? "optional" : ""}
              onChange={(e) =>
                setInputs((arr) =>
                  arr.map((v, idx) => (idx === i ? e.target.value : v))
                )
              }
            />
          </div>
        ))}
        <div className="flex items-end">
          <button
            type="button"
            onClick={compare}
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? "Loading…" : "Compare"}
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
          {error}
        </p>
      )}

      {rows.length > 0 && (
        <div className="-mx-6 mt-8 overflow-x-auto px-6">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="pb-3 pr-4 font-semibold">Metric</th>
                {rows.map((r) => (
                  <th key={r.symbol} className="pb-3 pr-4 text-right font-semibold">
                    <Link
                      href={`/stocks/${r.symbol}`}
                      className="text-brand hover:underline"
                    >
                      {r.symbol}
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              <tr>
                <td className="py-3 pr-4 font-medium">Price</td>
                {rows.map((r) => (
                  <td
                    key={r.symbol}
                    className="py-3 pr-4 text-right tabular-nums"
                  >
                    {money(r.quote?.price, r.currency_symbol)}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="py-3 pr-4 font-medium">Change</td>
                {rows.map((r) => {
                  const c = r.quote?.change ?? null;
                  const tone =
                    c == null
                      ? ""
                      : c >= 0
                      ? "text-ticker-up"
                      : "text-ticker-down";
                  return (
                    <td
                      key={r.symbol}
                      className={`py-3 pr-4 text-right tabular-nums ${tone}`}
                    >
                      {c == null ? "—" : `${c >= 0 ? "+" : ""}${ratio(c)}`}
                    </td>
                  );
                })}
              </tr>
              {METRICS.map((m) => (
                <tr key={m.key}>
                  <td className="py-3 pr-4 font-medium">{m.label}</td>
                  {rows.map((r) => (
                    <td
                      key={r.symbol}
                      className="py-3 pr-4 text-right tabular-nums"
                    >
                      {metricValue(
                        (r.overview as Record<string, number | null> | null)?.[
                          m.key
                        ],
                        m.unit
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
function PositionSizing() {
  const [capital, setCapital] = useState(200000);
  const [riskPct, setRiskPct] = useState(1);
  const [entry, setEntry] = useState(500);
  const [stop, setStop] = useState(470);

  const riskAmount = (capital * riskPct) / 100;
  const perShareRisk = entry - stop;
  const shares = perShareRisk > 0 ? Math.floor(riskAmount / perShareRisk) : 0;
  const positionValue = shares * entry;
  const exposurePct = capital > 0 ? (positionValue / capital) * 100 : 0;

  return (
    <div className="card">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Account capital" value={capital} onChange={setCapital} min={0} />
        <Field
          label="Risk per trade (%)"
          value={riskPct}
          onChange={setRiskPct}
          step={0.1}
          min={0}
        />
        <Field label="Entry price" value={entry} onChange={setEntry} step={0.05} min={0} />
        <Field label="Stop price" value={stop} onChange={setStop} step={0.05} min={0} />
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-4">
        <Result label="Risk amount" value={compact(riskAmount)} />
        <Result
          label="Risk per share"
          value={perShareRisk > 0 ? perShareRisk.toFixed(2) : "—"}
        />
        <Result label="Shares" value={shares.toLocaleString()} highlight />
        <Result
          label="Position value"
          value={`${compact(positionValue)} (${exposurePct.toFixed(1)}%)`}
        />
      </div>

      {perShareRisk <= 0 && (
        <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
          The stop must sit below the entry for a long position.
        </p>
      )}
    </div>
  );
}

/* --------------------------- shared bits --------------------------- */
function Field({
  label,
  value,
  onChange,
  step = 1,
  min,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        type="number"
        className="input"
        value={Number.isNaN(value) ? "" : value}
        step={step}
        min={min}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function Result({
  label,
  value,
  highlight = false,
  tone,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  tone?: "up" | "down";
}) {
  const toneClass =
    tone === "up"
      ? "text-ticker-up"
      : tone === "down"
      ? "text-ticker-down"
      : highlight
      ? "text-brand"
      : "text-slate-900 dark:text-slate-100";

  return (
    <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-800/50">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${toneClass}`}>
        {value}
      </p>
    </div>
  );
}
