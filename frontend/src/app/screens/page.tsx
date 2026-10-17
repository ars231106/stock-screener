"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import { metricValue } from "@/lib/format";
import type {
  Criterion,
  MetricsResponse,
  Operator,
  Preset,
  SavedScreen,
  ScreenRunResponse,
} from "@/lib/types";

export default function ScreensPage() {
  const { user } = useAuth();

  const [presets, setPresets] = useState<Preset[]>([]);
  const [meta, setMeta] = useState<MetricsResponse | null>(null);
  const [saved, setSaved] = useState<SavedScreen[]>([]);

  const [criteria, setCriteria] = useState<Criterion[]>([
    { metric: "pe_ratio", op: "lt", value: 25 },
  ]);
  const [results, setResults] = useState<ScreenRunResponse | null>(null);
  const [runningLabel, setRunningLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [screenName, setScreenName] = useState("");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    api.presets().then((r) => setPresets(r.presets)).catch(() => {});
    api.metrics().then(setMeta).catch(() => {});
  }, []);

  useEffect(() => {
    if (!user) {
      setSaved([]);
      return;
    }
    api.savedScreens().then(setSaved).catch(() => {});
  }, [user]);

  async function run(label: string, fn: () => Promise<ScreenRunResponse>) {
    setRunningLabel(label);
    setError(null);
    setResults(null);
    try {
      setResults(await fn());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The screen failed to run.");
    } finally {
      setRunningLabel(null);
    }
  }

  function updateCriterion(index: number, patch: Partial<Criterion>) {
    setCriteria((cs) =>
      cs.map((c, i) => (i === index ? { ...c, ...patch } : c))
    );
  }

  async function saveScreen() {
    if (!screenName.trim()) {
      setSaveMessage("Give the screen a name first.");
      return;
    }
    try {
      const created = await api.saveScreen({
        name: screenName.trim(),
        criteria,
      });
      setSaved((s) => [created, ...s]);
      setScreenName("");
      setSaveMessage("Saved.");
    } catch (err) {
      setSaveMessage(
        err instanceof ApiError ? err.message : "Could not save the screen."
      );
    }
  }

  async function deleteScreen(id: string) {
    try {
      await api.deleteScreen(id);
      setSaved((s) => s.filter((x) => x.id !== id));
    } catch {
      /* ignore */
    }
  }

  const metricLabel = (key: string) =>
    meta?.metrics.find((m) => m.key === key)?.label ?? key;
  const metricUnit = (key: string) =>
    meta?.metrics.find((m) => m.key === key)?.unit ?? "";

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="section-title">Stock screeners</h1>
      <p className="muted mt-2 max-w-2xl">
        Filter a universe of {meta?.universe_size ?? "—"} companies by their
        fundamentals. Every criterion must pass; a company missing a metric is
        excluded rather than assumed to pass.
      </p>

      {/* ------------------------- presets ------------------------- */}
      <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {presets.map((p) => (
          <div key={p.key} className="card card-hover flex flex-col">
            <h2 className="font-semibold text-slate-900 dark:text-slate-100">
              {p.name}
            </h2>
            <p className="muted mt-2 flex-1">{p.description}</p>
            <ul className="mt-4 space-y-1 text-xs text-slate-500 dark:text-slate-400">
              {p.criteria.map((c, i) => (
                <li key={i} className="flex items-center gap-1.5">
                  <span className="h-1 w-1 rounded-full bg-brand" />
                  {metricLabel(c.metric)} {opSymbol(c.op)}{" "}
                  {metricValue(c.value, metricUnit(c.metric))}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => run(p.key, () => api.runPreset(p.key))}
              disabled={runningLabel !== null}
              className="btn-primary mt-5"
            >
              {runningLabel === p.key ? "Running…" : "View stocks"}
            </button>
          </div>
        ))}
      </div>

      {/* --------------------- custom builder --------------------- */}
      <div className="card mt-10">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Build a custom screen
        </h2>

        <div className="mt-5 space-y-3">
          {criteria.map((c, i) => (
            <div
              key={i}
              className="flex flex-wrap items-end gap-3 rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50"
            >
              <div className="min-w-[180px] flex-1">
                <label className="label">Metric</label>
                <select
                  className="input"
                  value={c.metric}
                  onChange={(e) => updateCriterion(i, { metric: e.target.value })}
                >
                  {meta?.metrics.map((m) => (
                    <option key={m.key} value={m.key}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="w-40">
                <label className="label">Condition</label>
                <select
                  className="input"
                  value={c.op}
                  onChange={(e) =>
                    updateCriterion(i, { op: e.target.value as Operator })
                  }
                >
                  {meta?.operators.map((o) => (
                    <option key={o.key} value={o.key}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="w-32">
                <label className="label">
                  Value{metricUnit(c.metric) === "pct" ? " (0.15 = 15%)" : ""}
                </label>
                <input
                  type="number"
                  step="any"
                  className="input"
                  value={c.value}
                  onChange={(e) =>
                    updateCriterion(i, { value: Number(e.target.value) })
                  }
                />
              </div>

              {c.op === "between" && (
                <div className="w-32">
                  <label className="label">Upper</label>
                  <input
                    type="number"
                    step="any"
                    className="input"
                    value={c.value2 ?? 0}
                    onChange={(e) =>
                      updateCriterion(i, { value2: Number(e.target.value) })
                    }
                  />
                </div>
              )}

              <button
                type="button"
                onClick={() =>
                  setCriteria((cs) => cs.filter((_, idx) => idx !== i))
                }
                disabled={criteria.length === 1}
                className="btn-ghost text-red-600"
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() =>
              setCriteria((cs) => [
                ...cs,
                { metric: meta?.metrics[0]?.key ?? "pe_ratio", op: "gt", value: 0 },
              ])
            }
            className="btn-secondary"
          >
            + Add criterion
          </button>
          <button
            type="button"
            onClick={() => run("custom", () => api.runCustom(criteria))}
            disabled={runningLabel !== null}
            className="btn-primary"
          >
            {runningLabel === "custom" ? "Running…" : "Run screen"}
          </button>
        </div>

        {user && (
          <div className="mt-6 flex flex-wrap items-end gap-3 border-t border-slate-200 pt-5 dark:border-slate-800">
            <div className="min-w-[220px] flex-1">
              <label className="label">Save this screen as</label>
              <input
                className="input"
                placeholder="e.g. Cheap profitable compounders"
                value={screenName}
                onChange={(e) => setScreenName(e.target.value)}
              />
            </div>
            <button type="button" onClick={saveScreen} className="btn-secondary">
              Save
            </button>
            {saveMessage && <span className="muted">{saveMessage}</span>}
          </div>
        )}

        {!user && (
          <p className="muted mt-6 border-t border-slate-200 pt-5 dark:border-slate-800">
            <Link href="/login" className="text-brand hover:underline">
              Log in
            </Link>{" "}
            to save screens to your account.
          </p>
        )}
      </div>

      {/* --------------------- saved screens --------------------- */}
      {user && saved.length > 0 && (
        <div className="card mt-8">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Your saved screens
          </h2>
          <ul className="mt-4 divide-y divide-slate-200 dark:divide-slate-800">
            {saved.map((s) => (
              <li
                key={s.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div>
                  <p className="font-medium text-slate-800 dark:text-slate-100">
                    {s.name}
                  </p>
                  <p className="muted text-xs">
                    {s.criteria.length} criteria ·{" "}
                    {new Date(s.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      run(s.id, () => api.runSavedScreen(s.id))
                    }
                    disabled={runningLabel !== null}
                    className="btn-secondary"
                  >
                    {runningLabel === s.id ? "Running…" : "Run"}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteScreen(s.id)}
                    className="btn-ghost text-red-600"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ------------------------- results ------------------------- */}
      {error && (
        <div className="card mt-8 border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
          <p className="text-sm text-amber-700 dark:text-amber-300">{error}</p>
        </div>
      )}

      {results && (
        <div className="card mt-8 overflow-hidden">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {results.matched} match{results.matched === 1 ? "" : "es"}
            </h2>
            <p className="muted">
              {results.truncated
                ? `showing top ${results.returned} of ${results.matched} · `
                : ""}
              {results.evaluated} companies evaluated
            </p>
          </div>

          {results.message && (
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
              {results.message}
            </p>
          )}

          {results.results.length === 0 ? (
            <p className="muted mt-4">
              Nothing passed every criterion. Try loosening one of them.
            </p>
          ) : (
            <div className="mt-5 -mx-6 overflow-x-auto px-6">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <th className="pb-3 pr-4 font-semibold">Company</th>
                    <th className="pb-3 pr-4 font-semibold">Sector</th>
                    <th className="pb-3 pr-4 text-right font-semibold">Price</th>
                    <th className="pb-3 pr-4 text-right font-semibold">Change</th>
                    {Object.keys(results.results[0].metrics).map((m) => (
                      <th key={m} className="pb-3 pr-4 text-right font-semibold">
                        {metricLabel(m)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {results.results.map((row) => {
                    const up = (row.change_percent || "").startsWith("-")
                      ? "text-ticker-down"
                      : "text-ticker-up";
                    return (
                      <tr key={row.symbol}>
                        <td className="py-3 pr-4">
                          <Link
                            href={`/stocks/${row.symbol}`}
                            className="font-medium text-brand hover:underline"
                          >
                            {row.symbol}
                          </Link>
                          <span className="muted block max-w-[200px] truncate text-xs">
                            {row.name}
                          </span>
                        </td>
                        <td className="muted py-3 pr-4">{row.sector || "—"}</td>
                        <td className="py-3 pr-4 text-right tabular-nums">
                          {row.price != null ? row.price.toFixed(2) : "—"}
                        </td>
                        <td className={`py-3 pr-4 text-right tabular-nums ${up}`}>
                          {row.change_percent || "—"}
                        </td>
                        {Object.entries(row.metrics).map(([key, value]) => (
                          <td
                            key={key}
                            className="py-3 pr-4 text-right tabular-nums"
                          >
                            {metricValue(value, metricUnit(key))}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function opSymbol(op: Operator): string {
  switch (op) {
    case "gt":
      return ">";
    case "gte":
      return "≥";
    case "lt":
      return "<";
    case "lte":
      return "≤";
    case "eq":
      return "=";
    case "between":
      return "between";
  }
}
