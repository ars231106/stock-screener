# Stock Screener

A full-stack equity research tool: search any listed company, read its
fundamentals, run screens against a universe of stocks, and keep a watchlist
that persists across devices.

Rebuilt from a single-page vanilla JS prototype into a deployed three-tier
application.

| Tier | Stack | Hosted on |
|---|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind | Vercel |
| Backend | FastAPI, Python 3.11, httpx | Render |
| Database & auth | Supabase (Postgres + GoTrue), row-level security | Supabase |

Deployment instructions: **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

---

## What it does

- **Search** — type-ahead over company names and tickers, debounced so it
  does not burn the upstream rate limit on every keystroke.
- **Stock detail** — live quote (open/high/low/previous close/volume) plus
  fundamentals: P/E, P/B, PEG, EPS, margins, ROE, ROA, growth, beta,
  52-week range.
- **Screens** — four presets (growth, value, dividend, quality compounders)
  that actually execute, plus a criteria builder over 13 metrics with six
  operators. Save a screen and re-run it later.
- **Watchlist** — per-user, stored in Postgres, quotes attached on load.
- **Search history** — every lookup recorded against your account.
- **Tools** — return calculator, side-by-side stock comparison, and
  risk-based position sizing.
- **Theme** — light/dark, remembered, applied before first paint so there is
  no white flash.

---

## What changed from the prototype

The original was `index.html` + `script.js` + `style.css` talking straight to
Alpha Vantage from the browser. Three things about it could not survive
being deployed:

1. **The API key was in the client.** `script.js` line 17 shipped the Alpha
   Vantage key to every visitor. Anyone could read it from view-source and
   spend the quota. It now lives only in Render's environment; the browser
   talks to our own API.

2. **Auth was `localStorage`.** Passwords were stored in plaintext under
   `user_<username>`, and "logged in" meant a key existed in the same
   storage the user controls — so anyone could grant it to themselves from
   the console. Auth is now Supabase GoTrue: hashed passwords, real JWTs,
   verified server-side on every protected route.

3. **Nothing persisted.** Clear your browser and the account and watchlist
   were gone; there was no way to see the same list on your phone. State is
   now in Postgres, keyed to a user id.

Beyond the fixes: the Screens and Tools tabs, which previously popped
"available soon" alerts, are implemented.

---

## Architecture

```
Browser (Vercel)
  │
  │  1. signs in directly with Supabase Auth → receives a JWT
  │  2. calls the API with  Authorization: Bearer <jwt>
  ▼
FastAPI (Render)
  │  verifies the JWT locally with the project's JWT secret (no round-trip)
  │  scopes every query by the user id inside that token
  ├──────────────► Supabase Postgres   (service-role key, server only)
  └──────────────► Alpha Vantage       (API key, server only)
                     └─ responses cached in Postgres
```

**Why the cache is in Postgres rather than in memory:** Render's free tier
restarts the process regularly and an in-memory cache dies with it. Postgres
also means every user shares the cache, so the second person to look up
`AAPL` pays nothing for it.

**Why the backend proxies market data at all:** it keeps the provider key
server-side, lets one place handle rate limits and stale-fallback, and
normalises Alpha Vantage's awkward `"05. price"` field names into a clean
schema the frontend can type.

---

## Project layout

```
├── backend/                  FastAPI service (Render)
│   ├── app/
│   │   ├── core/             config, Supabase client, JWT verification
│   │   ├── routers/          stocks, watchlist, screens, users
│   │   ├── services/         market data + cache, screening engine
│   │   ├── schemas.py        Pydantic request/response models
│   │   └── main.py           app, CORS, health check
│   ├── requirements.txt
│   └── render.yaml           infrastructure-as-code for Render
│
├── frontend/                 Next.js app (Vercel)
│   └── src/
│       ├── app/              routes: /, /search, /stocks/[symbol],
│       │                     /screens, /tools, /watchlist, /history,
│       │                     /login, /learn, /about
│       ├── components/       Navbar, Footer, SearchBar, providers
│       └── lib/              typed API client, Supabase client, formatters
│
├── supabase/migrations/      SQL schema, RLS policies, triggers
└── DEPLOYMENT.md
```

---

## API

Interactive docs at `/docs` once the backend is running.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | — | Readiness; reports which env vars landed |
| GET | `/api/stocks/search?q=` | optional | Company/ticker search |
| GET | `/api/stocks/{symbol}` | optional | Quote + fundamentals + watchlist flag |
| GET | `/api/stocks/{symbol}/quote` | — | Price snapshot |
| GET | `/api/stocks/{symbol}/overview` | — | Fundamentals |
| GET | `/api/screens/metrics` | — | Screenable metrics and operators |
| GET | `/api/screens/presets` | — | Built-in screens |
| POST | `/api/screens/presets/{key}/run` | — | Run a preset |
| POST | `/api/screens/run` | — | Run ad-hoc criteria |
| GET/POST | `/api/screens/saved` | required | List / create saved screens |
| POST | `/api/screens/saved/{id}/run` | required | Run a saved screen |
| GET/POST | `/api/watchlist` | required | List / add |
| DELETE | `/api/watchlist/{symbol}` | required | Remove |
| GET/PATCH | `/api/me` | required | Profile |
| GET/DELETE | `/api/me/history` | required | Search history |

Routes marked *optional* work anonymously and personalise when a token is
present — the stock page uses this to show the watchlist state without
requiring a login to view prices.

---

## Data model

| Table | Holds |
|---|---|
| `profiles` | 1:1 with `auth.users`, created by a trigger on signup |
| `watchlists` / `watchlist_items` | Symbols per user |
| `saved_screens` | Named criteria sets (`jsonb`) |
| `search_history` | What each user looked up |
| `quote_cache` / `symbol_search_cache` | Shared upstream cache |

Every user-owned table has RLS enabled with `auth.uid() = user_id`
policies, so even a leaked anon key cannot read another user's rows.

---

## Known limits

- **Alpha Vantage free tier is ~25 requests/day.** Caching hides this for
  ordinary browsing; a cold custom screen can still hit it. When it does,
  the API returns 429 and the UI falls back to the last cached values rather
  than showing an error.
- **Fundamentals coverage is US-centric.** Indian tickers are searchable and
  quotable but usually return no `OVERVIEW`, so they cannot be screened.
  This is a provider limitation, not a code one — the screening engine takes
  its universe from one list in `services/screener.py`.
- **Render free tier sleeps** after 15 minutes idle; the first request then
  takes 30–50 seconds.

---

Market data is delayed and provided for educational purposes. Nothing here
is investment advice.
