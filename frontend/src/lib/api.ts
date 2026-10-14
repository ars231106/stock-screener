"use client";

import { getSupabaseClient } from "./supabase";
import type {
  MetricsResponse,
  Preset,
  Profile,
  SavedScreen,
  ScreenRunResponse,
  SearchHistoryEntry,
  SearchResponse,
  StockDetail,
  Criterion,
  WatchlistItem,
} from "./types";

const BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const supabase = getSupabaseClient();
  if (!supabase) return {};
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = false, headers, ...rest } = options;
  const extra = auth ? await authHeader() : {};

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...extra,
        ...(headers as Record<string, string>),
      },
    });
  } catch {
    throw new ApiError(
      0,
      "Could not reach the API. If the backend is on Render's free tier it may " +
        "be waking from sleep — give it about 30 seconds and try again."
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    const detail =
      (body as { detail?: string })?.detail ||
      (typeof body === "string" ? body : "") ||
      `Request failed with status ${res.status}`;
    throw new ApiError(res.status, detail);
  }

  return body as T;
}

// ----------------------------- stocks ------------------------------------
export const api = {
  search: (q: string) =>
    request<SearchResponse>(`/api/stocks/search?q=${encodeURIComponent(q)}`, {
      auth: true,
    }),

  stock: (symbol: string) =>
    request<StockDetail>(`/api/stocks/${encodeURIComponent(symbol)}`, {
      auth: true,
    }),

  // ---------------------------- watchlist --------------------------------
  watchlist: (withQuotes = true) =>
    request<WatchlistItem[]>(`/api/watchlist?with_quotes=${withQuotes}`, {
      auth: true,
    }),

  addToWatchlist: (payload: {
    symbol: string;
    company_name?: string | null;
    region?: string | null;
    currency?: string | null;
  }) =>
    request<WatchlistItem>("/api/watchlist", {
      method: "POST",
      body: JSON.stringify(payload),
      auth: true,
    }),

  removeFromWatchlist: (symbol: string) =>
    request<void>(`/api/watchlist/${encodeURIComponent(symbol)}`, {
      method: "DELETE",
      auth: true,
    }),

  // ------------------------------ screens --------------------------------
  metrics: () => request<MetricsResponse>("/api/screens/metrics"),

  presets: () => request<{ presets: Preset[] }>("/api/screens/presets"),

  runPreset: (key: string) =>
    request<ScreenRunResponse>(
      `/api/screens/presets/${encodeURIComponent(key)}/run`,
      { method: "POST" }
    ),

  runCustom: (criteria: Criterion[], limit = 25) =>
    request<ScreenRunResponse>("/api/screens/run", {
      method: "POST",
      body: JSON.stringify({ criteria, limit }),
    }),

  savedScreens: () => request<SavedScreen[]>("/api/screens/saved", { auth: true }),

  saveScreen: (payload: {
    name: string;
    description?: string;
    criteria: Criterion[];
  }) =>
    request<SavedScreen>("/api/screens/saved", {
      method: "POST",
      body: JSON.stringify(payload),
      auth: true,
    }),

  runSavedScreen: (id: string) =>
    request<ScreenRunResponse>(
      `/api/screens/saved/${encodeURIComponent(id)}/run`,
      { method: "POST", auth: true }
    ),

  deleteScreen: (id: string) =>
    request<void>(`/api/screens/saved/${encodeURIComponent(id)}`, {
      method: "DELETE",
      auth: true,
    }),

  // ------------------------------- me ------------------------------------
  profile: () => request<Profile>("/api/me", { auth: true }),

  history: (limit = 20) =>
    request<SearchHistoryEntry[]>(`/api/me/history?limit=${limit}`, {
      auth: true,
    }),

  clearHistory: () =>
    request<void>("/api/me/history", { method: "DELETE", auth: true }),
};

export const API_BASE = BASE;
