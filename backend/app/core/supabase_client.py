"""Lazily-created Supabase client using the service-role key.

The service role bypasses Row Level Security, which is what we want on the
server: every query in this codebase is explicitly scoped by ``user_id``
taken from a *verified* JWT, never from client input.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_supabase() -> Client | None:
    if not settings.is_configured:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_key)


def require_supabase() -> Client:
    client = get_supabase()
    if client is None:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_KEY in the environment."
        )
    return client
