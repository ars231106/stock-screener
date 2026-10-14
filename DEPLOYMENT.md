# Deployment guide

Roughly 25 minutes end to end. Do the steps in order — each one produces a
value the next one needs.

Order: **Supabase → Alpha Vantage → GitHub → Render → Vercel → link the two.**

---

## 0. Prerequisites

- A GitHub account
- Node 18+ and Python 3.11 locally (only if you want to run it before deploying)
- Free accounts on [supabase.com](https://supabase.com),
  [render.com](https://render.com) and [vercel.com](https://vercel.com)

---

## 1. Supabase — database and auth

1. Go to **supabase.com → New project**. Name it `stock-screener`, pick a
   region near you (Mumbai / Singapore for India), and set a database
   password. Save that password somewhere; you will not be shown it again.
   Provisioning takes about two minutes.

2. Open **SQL Editor → New query**. Paste the entire contents of
   `supabase/migrations/0001_init.sql` and press **Run**. You should see
   "Success. No rows returned."

3. Confirm it worked: **Table Editor** should now list `profiles`,
   `watchlists`, `watchlist_items`, `saved_screens`, `search_history`,
   `quote_cache` and `symbol_search_cache`.

4. **Authentication → Providers → Email** — make sure Email is enabled.
   While you are testing, turn **Confirm email** *off* (Authentication →
   Sign In / Providers → Email). Otherwise every test signup needs a
   round-trip through your inbox. Turn it back on before you share the site.

5. Collect four values. **Project Settings → API**:

   | Value | Where | Used by |
   |---|---|---|
   | Project URL | API → Project URL | both |
   | `anon` public key | API → Project API keys | frontend |
   | `service_role` key | API → Project API keys (click *Reveal*) | backend only |
   | JWT Secret | API → JWT Settings → JWT Secret | backend only |

   > The `service_role` key bypasses row-level security. It goes on Render
   > and nowhere else — never into the frontend, never into git.

---

## 2. Alpha Vantage — market data key

Get a free key at <https://www.alphavantage.co/support/#api-key>. It arrives
instantly.

The free tier allows about 25 requests per day. The backend caches every
quote and every company overview in Postgres precisely because of this, so
normal browsing will not exhaust it — but running several custom screens
against a cold cache can. If you want the screener to feel fast for other
people, the premium tier is worth it.

---

## 3. Push to GitHub

From the project folder:

```bash
git init
git add .
git commit -m "Full-stack stock screener: FastAPI + Next.js + Supabase"
git branch -M main
git remote add origin https://github.com/ars231106/stock-screener.git
git push -u origin main
```

Create the empty repo on GitHub first (no README, no .gitignore — this repo
has both).

Check before pushing that `git status` does **not** list any `.env` file.
The `.gitignore` covers them, but look anyway.

---

## 4. Render — the backend

1. **render.com → New → Web Service → Build and deploy from a Git
   repository**, and pick your repo.

2. Settings:

   | Field | Value |
   |---|---|
   | Name | `stock-screener-api` |
   | Region | Singapore (closest to India) |
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | Free |

3. **Environment variables** — add these before the first deploy:

   ```
   SUPABASE_URL          = https://YOUR-REF.supabase.co
   SUPABASE_SERVICE_KEY  = <service_role key>
   SUPABASE_ANON_KEY     = <anon key>
   SUPABASE_JWT_SECRET   = <JWT secret>
   ALPHA_VANTAGE_KEY     = <your key>
   CORS_ORIGINS          = http://localhost:3000
   ENVIRONMENT           = production
   PYTHON_VERSION        = 3.11.9
   ```

   Leave `CORS_ORIGINS` as-is for now; you will add the Vercel URL in step 6.

4. **Create Web Service**. The first build takes 3–5 minutes.

5. Verify. Open `https://stock-screener-api.onrender.com/health` — you want:

   ```json
   {
     "status": "healthy",
     "supabase_configured": true,
     "supabase_reachable": true,
     "jwt_secret_set": true,
     "market_data_key_set": true
   }
   ```

   Any `false` there names the environment variable you got wrong. The
   interactive API docs are at `/docs`.

   > **Free tier caveat:** Render sleeps a free service after 15 minutes of
   > inactivity, and the next request takes 30–50 seconds to wake it. The
   > frontend shows a message saying so rather than a bare error. For a
   > portfolio link people will click cold, either upgrade or use a cron
   > ping (e.g. cron-job.org hitting `/health` every 10 minutes).

---

## 5. Vercel — the frontend

1. **vercel.com → Add New → Project**, import the same repo.

2. Settings:

   | Field | Value |
   |---|---|
   | Framework Preset | Next.js |
   | Root Directory | `frontend` |

   Leave build and output settings on their defaults.

3. **Environment Variables**:

   ```
   NEXT_PUBLIC_SUPABASE_URL      = https://YOUR-REF.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY = <anon key>
   NEXT_PUBLIC_API_URL           = https://stock-screener-api.onrender.com
   ```

   `NEXT_PUBLIC_API_URL` must have **no trailing slash**.

   These are baked in at build time, so changing one later means
   redeploying, not just saving.

4. **Deploy**. You get a URL like `https://stock-screener-xyz.vercel.app`.

---

## 6. Link the two

1. Back on **Render → your service → Environment**, set:

   ```
   CORS_ORIGINS = http://localhost:3000,https://stock-screener-xyz.vercel.app
   ```

   Use your real Vercel URL. Save — Render redeploys automatically.
   (Preview deployments on `*.vercel.app` are already allowed by a regex in
   `main.py`, so you only need to list the production URL.)

2. In **Supabase → Authentication → URL Configuration**:
   - **Site URL**: your Vercel URL
   - **Redirect URLs**: add `https://stock-screener-xyz.vercel.app/**`

   This is what makes email confirmation links come back to your site
   rather than to localhost.

---

## 7. Verify end to end

Open your Vercel URL and walk through:

- [ ] Home page loads, dark/light toggle works and survives a refresh
- [ ] Typing "apple" in the search box shows suggestions after a moment
- [ ] Clicking a suggestion opens the stock page with price and fundamentals
- [ ] **Get New Account** → sign up → you land on the watchlist
- [ ] **Add to watchlist** on a stock page, then check `/watchlist`
- [ ] `/screens` → **View stocks** on the Value preset returns rows
- [ ] Build a custom screen, run it, save it, run the saved one
- [ ] Log out and back in — the watchlist is still there
- [ ] In Supabase **Table Editor**, `watchlist_items` shows your row

If the first request after a quiet period fails, that is Render's free tier
waking up. Wait 40 seconds and retry before debugging anything.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not reach the API" | Render asleep, or `NEXT_PUBLIC_API_URL` wrong | Wait 40s; check the URL has no trailing slash |
| CORS error in the browser console | Vercel URL missing from `CORS_ORIGINS` | Add it on Render, exactly, with `https://` and no trailing slash |
| 401 on watchlist while logged in | `SUPABASE_JWT_SECRET` wrong on Render | Re-copy from Project Settings → API → JWT Settings |
| `/health` says `supabase_reachable: false` | Migration never ran, or service key wrong | Re-run the SQL; re-copy the `service_role` key |
| 429 "rate limit reached" | Alpha Vantage daily cap | Wait, or upgrade the key. Cached symbols keep working |
| Signup succeeds but login fails | Email confirmation is on | Confirm via the emailed link, or turn confirmation off while testing |
| Screens return 0 matches | Fundamentals missing for the universe | Presets cover US tickers; Indian listings rarely publish an OVERVIEW |

---

## Running it locally

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then fill it in
uvicorn app.main:app --reload
```

API on <http://localhost:8000>, docs on <http://localhost:8000/docs>.

**Frontend** (in a second terminal):

```bash
cd frontend
npm install
copy .env.example .env.local    # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Site on <http://localhost:3000>.
