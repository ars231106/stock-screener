"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { SearchHistoryEntry } from "@/lib/types";

export default function HistoryPage() {
  const { user, loading: authLoading } = useAuth();
  const [entries, setEntries] = useState<SearchHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    api
      .history(50)
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  async function clear() {
    await api.clearHistory().catch(() => {});
    setEntries([]);
  }

  if (authLoading || loading) {
    return <p className="muted mx-auto max-w-3xl px-4 py-12">Loading…</p>;
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <h1 className="section-title">Search history</h1>
        <p className="muted mt-3">Log in to see what you have been looking at.</p>
        <Link href="/login" className="btn-primary mt-6 inline-flex">
          Log in
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="section-title">Search history</h1>
        {entries.length > 0 && (
          <button type="button" onClick={clear} className="btn-ghost text-red-600">
            Clear history
          </button>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="muted mt-6">Nothing yet.</p>
      ) : (
        <ul className="card mt-6 divide-y divide-slate-100 dark:divide-slate-800">
          {entries.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-800 dark:text-slate-100">
                  {e.company_name || e.query}
                </p>
                <p className="muted text-xs">
                  searched &ldquo;{e.query}&rdquo; · {timeAgo(e.searched_at)}
                </p>
              </div>
              {e.symbol && (
                <Link
                  href={`/stocks/${e.symbol}`}
                  className="shrink-0 text-sm font-medium text-brand hover:underline"
                >
                  {e.symbol} →
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
