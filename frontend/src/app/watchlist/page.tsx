"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import SearchBar from "@/components/SearchBar";
import { api, ApiError } from "@/lib/api";
import { currencySymbol, money, ratio, volume } from "@/lib/format";
import type { WatchlistItem } from "@/lib/types";

export default function WatchlistPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await api.watchlist());
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not load your watchlist."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    load();
  }, [user, authLoading, load]);

  async function remove(symbol: string) {
    const previous = items;
    setItems((list) => list.filter((i) => i.symbol !== symbol)); // optimistic
    try {
      await api.removeFromWatchlist(symbol);
    } catch {
      setItems(previous);
      setError("Could not remove that symbol. Please try again.");
    }
  }

  if (authLoading || loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <div className="card animate-pulse space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 rounded bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center sm:px-6">
        <h1 className="section-title">Your watchlist</h1>
        <p className="muted mt-3">
          Sign in to keep a list of symbols that follows you across devices.
        </p>
        <Link href="/login" className="btn-primary mt-6 inline-flex">
          Log in or sign up
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="section-title">Your watchlist</h1>
        <button type="button" onClick={load} className="btn-secondary">
          ↻ Refresh quotes
        </button>
      </div>

      <div className="mt-6">
        <SearchBar size="sm" placeholder="Find a company to add…" />
      </div>

      {error && (
        <div className="card mt-6 border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
          <p className="text-sm text-amber-700 dark:text-amber-300">{error}</p>
        </div>
      )}

      {items.length === 0 ? (
        <div className="card mt-8 text-center">
          <p className="muted">
            Nothing here yet. Search for a company and press{" "}
            <span className="font-medium">Add to watchlist</span> on its page.
          </p>
        </div>
      ) : (
        <div className="card mt-8 overflow-hidden">
          <div className="-mx-6 overflow-x-auto px-6">
            <table className="w-full min-w-[680px] text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                  <th className="pb-3 pr-4 font-semibold">Symbol</th>
                  <th className="pb-3 pr-4 text-right font-semibold">Price</th>
                  <th className="pb-3 pr-4 text-right font-semibold">Change</th>
                  <th className="pb-3 pr-4 text-right font-semibold">Volume</th>
                  <th className="pb-3 pr-4 text-right font-semibold">Added</th>
                  <th className="pb-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {items.map((item) => {
                  const cs = currencySymbol(item.currency);
                  const change = item.quote?.change ?? null;
                  const tone =
                    change == null
                      ? "text-slate-500"
                      : change >= 0
                      ? "text-ticker-up"
                      : "text-ticker-down";
                  return (
                    <tr key={item.id}>
                      <td className="py-3 pr-4">
                        <Link
                          href={`/stocks/${item.symbol}`}
                          className="font-medium text-brand hover:underline"
                        >
                          {item.symbol}
                        </Link>
                        <span className="muted block max-w-[220px] truncate text-xs">
                          {item.company_name || item.region}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">
                        {money(item.quote?.price, cs)}
                      </td>
                      <td className={`py-3 pr-4 text-right tabular-nums ${tone}`}>
                        {change == null
                          ? "—"
                          : `${change >= 0 ? "+" : ""}${ratio(change)} ${
                              item.quote?.change_percent ?? ""
                            }`}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">
                        {volume(item.quote?.volume)}
                      </td>
                      <td className="muted py-3 pr-4 text-right">
                        {new Date(item.added_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          type="button"
                          onClick={() => remove(item.symbol)}
                          className="btn-ghost text-red-600"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
