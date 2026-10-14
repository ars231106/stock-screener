import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.supabase_client import get_supabase
from app.routers import screens, stocks, users, watchlist

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Backend for the Stock Screener. Serves market data (proxied and "
        "cached so the provider key never reaches the browser), the "
        "screening engine, watchlists and saved screens. Authentication is "
        "by Supabase-issued JWT."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",  # preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(screens.router)
app.include_router(users.router)


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "environment": settings.environment,
    }


@app.get("/health", tags=["meta"])
async def health():
    """Readiness probe. Render pings this; it also tells you at a glance
    whether the environment variables actually landed."""
    supabase_ok = False
    if get_supabase() is not None:
        try:
            get_supabase().table("quote_cache").select("symbol").limit(1).execute()
            supabase_ok = True
        except Exception as exc:
            log.warning("supabase health check failed: %s", exc)

    healthy = supabase_ok and bool(settings.supabase_jwt_secret)
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "degraded",
            "supabase_configured": settings.is_configured,
            "supabase_reachable": supabase_ok,
            "jwt_secret_set": bool(settings.supabase_jwt_secret),
            "market_data_key_set": settings.alpha_vantage_key not in ("", "demo"),
        },
    )
