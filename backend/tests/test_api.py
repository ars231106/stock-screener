"""Provider normalisation and API-surface contract tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _token(sub="11111111-1111-1111-1111-111111111111", **extra):
    return jwt.encode(
        {"sub": sub, "email": "a@b.co", "aud": "authenticated", **extra},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


class TestAuthBoundary:
    """Every protected route must reject an anonymous caller. This is the
    test that would have caught the original localStorage auth, where
    'logged in' meant a key existed in storage the user controlled."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/api/watchlist"),
            ("post", "/api/watchlist"),
            ("delete", "/api/watchlist/AAPL"),
            ("get", "/api/me"),
            ("patch", "/api/me"),
            ("get", "/api/me/history"),
            ("delete", "/api/me/history"),
            ("get", "/api/screens/saved"),
            ("post", "/api/screens/saved"),
        ],
    )
    def test_protected_routes_require_a_token(self, client, method, path):
        # GET/DELETE take no body in this client; only send one where it is legal.
        kwargs = {"json": {}} if method in ("post", "patch", "put") else {}
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 401, f"{method.upper()} {path} was not protected"

    def test_garbage_token_is_rejected(self, client):
        resp = client.get(
            "/api/watchlist", headers={"Authorization": "Bearer not.a.jwt"}
        )
        assert resp.status_code == 401

    def test_token_signed_with_the_wrong_secret_is_rejected(self, client):
        forged = jwt.encode(
            {"sub": "abc", "aud": "authenticated"}, "attacker-secret", algorithm="HS256"
        )
        resp = client.get("/api/watchlist", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401

    def test_token_for_the_wrong_audience_is_rejected(self, client):
        wrong = jwt.encode(
            {"sub": "abc", "aud": "some-other-service"},
            settings.supabase_jwt_secret,
            algorithm="HS256",
        )
        resp = client.get("/api/watchlist", headers={"Authorization": f"Bearer {wrong}"})
        assert resp.status_code == 401


class TestPublicRoutes:
    def test_root_is_open(self, client):
        assert client.get("/").status_code == 200

    def test_metrics_catalogue_is_open(self, client):
        resp = client.get("/api/screens/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["metrics"] and body["operators"]

    def test_presets_are_open(self, client):
        resp = client.get("/api/screens/presets")
        assert resp.status_code == 200
        assert {p["key"] for p in resp.json()["presets"]} >= {
            "growth", "value", "dividend", "quality"
        }


class TestInputValidation:
    def test_history_rejects_an_unknown_range(self, client):
        resp = client.get("/api/stocks/AAPL/history?range=forever")
        assert resp.status_code == 422

    def test_search_requires_a_query(self, client):
        assert client.get("/api/stocks/search").status_code == 422

    def test_empty_criteria_is_rejected(self, client):
        resp = client.post("/api/screens/run", json={"criteria": []})
        assert resp.status_code == 400


class TestYahooNormalisation:
    """The provider's job is to turn a vendor payload into our schema. These
    assert the conversions that have actually gone wrong."""

    def test_dividend_yield_is_scaled_to_a_decimal_fraction(self):
        """yfinance reports percent units. Apple's 0.32 means 0.32%, not
        32% -- the bug that shipped and had to be fixed in production."""
        from app.providers.yahoo import YahooProvider

        assert hasattr(YahooProvider, "overview")
        import inspect

        src = inspect.getsource(YahooProvider.overview)
        assert "dividend_yield / 100" in src or "dividend_yield = dividend_yield / 100" in src
        assert "> 1" not in src.split("dividendYield")[-1][:400], (
            "scaling must be unconditional: a `> 1` guard inflates low yields "
            "a hundredfold"
        )

    def test_region_mapping_for_indian_suffixes(self):
        from app.providers.yahoo import _region_for

        assert _region_for("TCS.NS", None) == "India/NSE"
        assert _region_for("TCS.BO", None) == "India/BSE"
        assert _region_for("AAPL", "NasdaqGS") == "NasdaqGS"
        assert _region_for("AAPL", None) == "United States"

    def test_history_ranges_cover_the_ui_tabs(self):
        from app.providers.yahoo import YahooProvider

        assert set(YahooProvider.RANGES) == {"1m", "6m", "1y", "3y", "5y", "10y", "max"}

    def test_long_ranges_use_coarser_bars(self):
        """A 10-year daily series is ~2500 points for ~900px of width."""
        from app.providers.yahoo import YahooProvider

        assert YahooProvider.RANGES["1y"][1] == "1d"
        assert YahooProvider.RANGES["10y"][1] == "1mo"


class TestAlphaVantageNormalisation:
    def test_rate_limit_is_detected_in_the_body_not_the_status(self):
        """Alpha Vantage returns HTTP 200 with a Note/Information field when
        throttled. Reading only the status code would treat the quota
        message as valid data."""
        import inspect

        from app.providers.alpha_vantage import AlphaVantageProvider

        src = inspect.getsource(AlphaVantageProvider._call)
        assert '"Note"' in src and '"Information"' in src

    async def test_history_is_explicitly_unsupported(self):
        from app.providers.alpha_vantage import AlphaVantageProvider
        from app.providers.base import NotSupportedError

        with pytest.raises(NotSupportedError):
            await AlphaVantageProvider("k").history("AAPL", "1y")


class TestConfig:
    def test_cors_origins_parse_into_a_list(self, monkeypatch):
        from app.core.config import Settings

        s = Settings(cors_origins="http://a.com, https://b.com ,")
        assert s.cors_origin_list == ["http://a.com", "https://b.com"]

    def test_provider_list_parses_and_trims(self):
        from app.core.config import Settings

        s = Settings(market_data_providers=" yahoo , alpha_vantage ")
        assert s.provider_list == ["yahoo", "alpha_vantage"]

    def test_is_configured_requires_url_and_service_key(self):
        from app.core.config import Settings

        assert not Settings(supabase_url="", supabase_service_key="k").is_configured
        assert not Settings(supabase_url="u", supabase_service_key="").is_configured
        assert Settings(supabase_url="u", supabase_service_key="k").is_configured
