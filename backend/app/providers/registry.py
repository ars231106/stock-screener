"""Chooses the active provider chain from configuration.

The chain is ordered: the first provider is tried, and on a *rate limit or
transport failure* -- not on a genuine "no such ticker" -- the next one is
tried. This is what keeps the app alive when one vendor degrades.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from app.core.config import settings
from app.providers.alpha_vantage import AlphaVantageProvider
from app.providers.base import MarketDataProvider
from app.providers.yahoo import YahooProvider

log = logging.getLogger(__name__)


def _build(name: str) -> MarketDataProvider | None:
    name = name.strip().lower()
    if name in ("yahoo", "yfinance"):
        return YahooProvider()
    if name in ("alpha_vantage", "alphavantage", "av"):
        if not settings.alpha_vantage_key:
            log.warning("alpha_vantage requested but no key is set; skipping")
            return None
        return AlphaVantageProvider(
            settings.alpha_vantage_key, settings.alpha_vantage_base
        )
    log.warning("unknown market data provider %r; skipping", name)
    return None


@lru_cache
def get_provider_chain() -> List[MarketDataProvider]:
    """Providers in priority order, built once per process."""
    chain = [p for p in (_build(n) for n in settings.provider_list) if p is not None]
    if not chain:
        log.warning("no providers configured; falling back to Yahoo")
        chain = [YahooProvider()]
    log.info("market data provider chain: %s", [p.name for p in chain])
    return chain
