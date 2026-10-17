from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, read from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "Stock Screener API"
    environment: str = "development"
    debug: bool = False

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_key: str = ""      # server-side only, bypasses RLS
    supabase_jwt_secret: str = ""       # used to verify user access tokens
    supabase_anon_key: str = ""

    # --- Market data providers ---
    # Comma-separated, in priority order. The first entry serves requests;
    # later entries are tried only when an earlier one is rate-limited or
    # unreachable. e.g. "yahoo,alpha_vantage"
    market_data_providers: str = "yahoo,alpha_vantage"

    alpha_vantage_key: str = ""
    alpha_vantage_base: str = "https://www.alphavantage.co/query"

    # Seconds a quote stays fresh in the shared cache before we hit the
    # upstream API again. Alpha Vantage free tier = 25 requests/day, so
    # keep this generous.
    quote_cache_ttl: int = 300
    search_cache_ttl: int = 86400
    overview_cache_ttl: int = 86400

    # --- CORS ---
    # Comma-separated list, e.g.
    # "http://localhost:3000,https://stock-screener.vercel.app"
    cors_origins: str = "http://localhost:3000"

    @property
    def provider_list(self) -> list[str]:
        return [p.strip() for p in self.market_data_providers.split(",") if p.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
