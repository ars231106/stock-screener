"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { SymbolMatch } from "@/lib/types";

interface Props {
  autoFocus?: boolean;
  placeholder?: string;
  size?: "lg" | "sm";
}

export default function SearchBar({
  autoFocus = false,
  placeholder = "Enter company name or stock symbol",
  size = "lg",
}: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<SymbolMatch[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlight, setHighlight] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced type-ahead. 350ms is long enough to avoid burning the
  // upstream rate limit on every keystroke.
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setMatches([]);
      setError(null);
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.search(trimmed);
        setMatches(res.matches.slice(0, 8));
        setOpen(true);
        setHighlight(-1);
      } catch (err) {
        setMatches([]);
        setError(err instanceof ApiError ? err.message : "Search failed.");
        setOpen(true);
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => clearTimeout(handle);
  }, [query]);

  // Close the dropdown on an outside click.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function go(symbol: string) {
    setOpen(false);
    router.push(`/stocks/${encodeURIComponent(symbol)}`);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    if (highlight >= 0 && matches[highlight]) {
      go(matches[highlight].symbol);
    } else if (matches.length > 0) {
      go(matches[0].symbol);
    } else {
      // No suggestions yet — treat the input as a ticker.
      go(trimmed.toUpperCase());
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || matches.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => (h + 1) % matches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => (h - 1 + matches.length) % matches.length);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const inputClasses =
    size === "lg"
      ? "w-full rounded-xl border border-slate-300 bg-white px-5 py-4 text-base shadow-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/30 dark:border-slate-700 dark:bg-surface-dark dark:text-slate-100 dark:placeholder:text-slate-500"
      : "w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/30 dark:border-slate-700 dark:bg-surface-dark dark:text-slate-100";

  return (
    <div ref={containerRef} className="relative mx-auto w-full max-w-2xl">
      <form onSubmit={onSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            autoFocus={autoFocus}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => matches.length > 0 && setOpen(true)}
            placeholder={placeholder}
            aria-label="Search for a company or ticker"
            className={inputClasses}
          />
          {loading && (
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-slate-400">
              searching…
            </span>
          )}
        </div>
        <button
          type="submit"
          className={`rounded-lg bg-brand font-semibold text-white transition hover:bg-brand-dark ${
            size === "lg" ? "px-6 py-4" : "px-4 py-2.5 text-sm"
          }`}
        >
          Search
        </button>
      </form>

      {open && (matches.length > 0 || error) && (
        <ul className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-surface-dark">
          {error && (
            <li className="px-4 py-3 text-sm text-amber-600 dark:text-amber-400">
              {error}
            </li>
          )}
          {matches.map((m, i) => (
            <li key={`${m.symbol}-${i}`}>
              <button
                type="button"
                onClick={() => go(m.symbol)}
                onMouseEnter={() => setHighlight(i)}
                className={`flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition ${
                  i === highlight
                    ? "bg-brand/10 dark:bg-brand/20"
                    : "hover:bg-slate-50 dark:hover:bg-slate-800"
                }`}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {m.name || m.symbol}
                  </span>
                  <span className="block text-xs text-slate-500 dark:text-slate-400">
                    {m.symbol} · {m.region}
                  </span>
                </span>
                <span className="shrink-0 rounded bg-slate-100 px-2 py-1 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  {m.currency}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
