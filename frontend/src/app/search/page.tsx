"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import SearchBar from "@/components/SearchBar";
import { api, ApiError } from "@/lib/api";
import type { SymbolMatch } from "@/lib/types";

function Results() {
  const params = useSearchParams();
  const query = params.get("q") ?? "";
  const [matches, setMatches] = useState<SymbolMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query.trim()) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .search(query)
      .then((res) => {
        if (!cancelled) setMatches(res.matches);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Search failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
      <SearchBar size="sm" placeholder="Search another company…" />

      <h1 className="section-title mt-10">
        Results for <span className="text-brand">{query}</span>
      </h1>

      {loading && <p className="muted mt-6">Searching…</p>}

      {error && (
        <div className="card mt-6 border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
          <p className="text-sm text-amber-700 dark:text-amber-300">{error}</p>
        </div>
      )}

      {!loading && !error && matches.length === 0 && query && (
        <p className="muted mt-6">
          No matching company found. Try a ticker symbol such as{" "}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">
            AAPL
          </code>{" "}
          or{" "}
          <code className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-800">
            TCS.BSE
          </code>
          .
        </p>
      )}

      <ul className="mt-6 space-y-3">
        {matches.map((m) => (
          <li key={m.symbol}>
            <Link
              href={`/stocks/${encodeURIComponent(m.symbol)}`}
              className="card card-hover flex items-center justify-between gap-4"
            >
              <span className="min-w-0">
                <span className="block truncate font-semibold text-slate-800 dark:text-slate-100">
                  {m.name || m.symbol}
                </span>
                <span className="muted block">
                  {m.symbol} · {m.region} · {m.type}
                </span>
              </span>
              <span className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {m.currency}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={<p className="muted mx-auto max-w-4xl px-4 py-12">Loading…</p>}
    >
      <Results />
    </Suspense>
  );
}
