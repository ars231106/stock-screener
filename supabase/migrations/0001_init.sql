-- =====================================================================
-- Stock Screener — initial schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. PROFILES  (1:1 with auth.users)
-- ---------------------------------------------------------------------
create table if not exists public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  username     text unique,
  display_name text,
  avatar_url   text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- Auto-create a profile row whenever a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, username, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1)),
    coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1))
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------
-- 2. WATCHLISTS
-- ---------------------------------------------------------------------
create table if not exists public.watchlists (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  name       text not null default 'My Watchlist',
  is_default boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists watchlists_user_idx on public.watchlists(user_id);

create table if not exists public.watchlist_items (
  id           uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references public.watchlists(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  symbol       text not null,
  company_name text,
  region       text,
  currency     text,
  notes        text,
  added_at     timestamptz not null default now(),
  unique (watchlist_id, symbol)
);
create index if not exists watchlist_items_user_idx on public.watchlist_items(user_id);
create index if not exists watchlist_items_list_idx on public.watchlist_items(watchlist_id);

-- ---------------------------------------------------------------------
-- 3. SAVED SCREENS  (custom screener criteria)
-- ---------------------------------------------------------------------
create table if not exists public.saved_screens (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  description text,
  -- e.g. [{"metric":"pe_ratio","op":"lt","value":15}, ...]
  criteria    jsonb not null default '[]'::jsonb,
  is_public   boolean not null default false,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists saved_screens_user_idx on public.saved_screens(user_id);

-- ---------------------------------------------------------------------
-- 4. SEARCH HISTORY
-- ---------------------------------------------------------------------
create table if not exists public.search_history (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  query        text not null,
  symbol       text,
  company_name text,
  searched_at  timestamptz not null default now()
);
create index if not exists search_history_user_time_idx
  on public.search_history(user_id, searched_at desc);

-- ---------------------------------------------------------------------
-- 5. QUOTE CACHE  (shared, server-written — shields the Alpha Vantage
--    free-tier rate limit of 25 requests/day)
-- ---------------------------------------------------------------------
create table if not exists public.quote_cache (
  symbol     text primary key,
  payload    jsonb not null,
  fetched_at timestamptz not null default now()
);

create table if not exists public.symbol_search_cache (
  query      text primary key,
  payload    jsonb not null,
  fetched_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 6. ROW LEVEL SECURITY
--    The backend uses the SERVICE ROLE key, which bypasses RLS. These
--    policies exist so the browser can also read its own rows safely
--    via the Supabase JS client if you ever want direct reads.
-- ---------------------------------------------------------------------
alter table public.profiles           enable row level security;
alter table public.watchlists         enable row level security;
alter table public.watchlist_items    enable row level security;
alter table public.saved_screens      enable row level security;
alter table public.search_history     enable row level security;
alter table public.quote_cache        enable row level security;
alter table public.symbol_search_cache enable row level security;

-- profiles
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);
drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id);

-- watchlists
drop policy if exists "watchlists_all_own" on public.watchlists;
create policy "watchlists_all_own" on public.watchlists
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- watchlist_items
drop policy if exists "watchlist_items_all_own" on public.watchlist_items;
create policy "watchlist_items_all_own" on public.watchlist_items
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- saved_screens: own rows, plus anyone may read public ones
drop policy if exists "saved_screens_all_own" on public.saved_screens;
create policy "saved_screens_all_own" on public.saved_screens
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "saved_screens_read_public" on public.saved_screens;
create policy "saved_screens_read_public" on public.saved_screens
  for select using (is_public = true);

-- search_history
drop policy if exists "search_history_all_own" on public.search_history;
create policy "search_history_all_own" on public.search_history
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- caches: readable by any signed-in user, writable only by service role
drop policy if exists "quote_cache_read" on public.quote_cache;
create policy "quote_cache_read" on public.quote_cache
  for select using (auth.role() = 'authenticated');
drop policy if exists "symbol_search_cache_read" on public.symbol_search_cache;
create policy "symbol_search_cache_read" on public.symbol_search_cache
  for select using (auth.role() = 'authenticated');

-- ---------------------------------------------------------------------
-- 7. updated_at maintenance
-- ---------------------------------------------------------------------
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_touch on public.profiles;
create trigger profiles_touch before update on public.profiles
  for each row execute function public.touch_updated_at();

drop trigger if exists saved_screens_touch on public.saved_screens;
create trigger saved_screens_touch before update on public.saved_screens
  for each row execute function public.touch_updated_at();
