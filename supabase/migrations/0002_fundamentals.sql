-- =====================================================================
-- Fundamentals store + screening universe
--
-- Why this exists: screening used to fetch company fundamentals from the
-- market data provider once per symbol, per request -- O(universe) upstream
-- calls for every screen. That does not survive real traffic on any
-- provider, and Yahoo refuses the fundamentals endpoint from datacenter
-- IPs outright, so the API server cannot fetch them at all.
--
-- Instead a scheduled job writes fundamentals here, and a screen becomes a
-- single indexed SQL query. Screening cost is now independent of universe
-- size, and the API server never talks to a provider for fundamentals.
-- =====================================================================

-- ---------------------------------------------------------------------
-- The set of symbols the screener considers.
-- ---------------------------------------------------------------------
create table if not exists public.universe (
  symbol     text primary key,
  name       text,
  market     text not null default 'US',   -- 'US' | 'IN'
  exchange   text,
  currency   text,
  active     boolean not null default true,
  added_at   timestamptz not null default now()
);
create index if not exists universe_active_idx on public.universe(active, market);

-- ---------------------------------------------------------------------
-- One row per symbol, refreshed on a schedule.
-- Metrics are real columns rather than jsonb so they can be indexed and
-- filtered with ordinary SQL predicates.
-- ---------------------------------------------------------------------
create table if not exists public.fundamentals (
  symbol              text primary key references public.universe(symbol) on delete cascade,
  name                text,
  exchange            text,
  currency            text,
  country             text,
  sector              text,
  industry            text,
  description         text,

  market_cap          double precision,
  pe_ratio            double precision,
  peg_ratio           double precision,
  pb_ratio            double precision,
  eps                 double precision,
  book_value          double precision,
  dividend_yield      double precision,
  dividend_per_share  double precision,
  profit_margin       double precision,
  operating_margin    double precision,
  roe                 double precision,
  roa                 double precision,
  revenue_ttm         double precision,
  revenue_growth_yoy  double precision,
  earnings_growth_yoy double precision,
  beta                double precision,
  week_52_high        double precision,
  week_52_low         double precision,

  source              text,               -- which provider supplied this row
  updated_at          timestamptz not null default now()
);

-- Indexes on the metrics screens filter by most often. Partial indexes
-- skip the nulls, which are common -- not every company publishes every
-- figure, and a null must never pass a criterion.
create index if not exists fundamentals_pe_idx     on public.fundamentals(pe_ratio)       where pe_ratio is not null;
create index if not exists fundamentals_pb_idx     on public.fundamentals(pb_ratio)       where pb_ratio is not null;
create index if not exists fundamentals_roe_idx    on public.fundamentals(roe)            where roe is not null;
create index if not exists fundamentals_divy_idx   on public.fundamentals(dividend_yield) where dividend_yield is not null;
create index if not exists fundamentals_mcap_idx   on public.fundamentals(market_cap)     where market_cap is not null;
create index if not exists fundamentals_sector_idx on public.fundamentals(sector);
create index if not exists fundamentals_stale_idx  on public.fundamentals(updated_at);

-- ---------------------------------------------------------------------
-- RLS: both tables are public reference data. Readable by anyone,
-- writable only by the service role (which bypasses RLS entirely).
-- ---------------------------------------------------------------------
alter table public.universe     enable row level security;
alter table public.fundamentals enable row level security;

drop policy if exists "universe_read" on public.universe;
create policy "universe_read" on public.universe for select using (true);

drop policy if exists "fundamentals_read" on public.fundamentals;
create policy "fundamentals_read" on public.fundamentals for select using (true);

drop trigger if exists fundamentals_touch on public.fundamentals;
create trigger fundamentals_touch before update on public.fundamentals
  for each row execute function public.touch_updated_at();
