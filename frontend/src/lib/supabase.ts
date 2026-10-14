"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let client: SupabaseClient | null = null;

/**
 * Browser-side Supabase client, created once.
 *
 * Returns null when the environment variables are missing so the app can
 * render a clear "not configured" message instead of throwing at import
 * time — which is what you want the first time you deploy and forget a
 * variable.
 */
export function getSupabaseClient(): SupabaseClient | null {
  if (!url || !anonKey) return null;
  if (!client) {
    client = createBrowserClient(url, anonKey);
  }
  return client;
}

export const isSupabaseConfigured = Boolean(url && anonKey);
