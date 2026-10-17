"""Market data: cache behaviour, provider fallback, and SMA alignment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.providers.base import ProviderError, RateLimitError, to_float, to_int
from app.services import market_data


class TestNumericCoercion:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("12.5", 12.5), (3, 3.0), (None, None), ("None", None),
            ("-", None), ("", None), ("N/A", None), ("not a number", None),
            (float("nan"), None),  # a NaN must not survive as a metric
        ],
    )
    def test_to_float(self, raw, expected):
        assert to_float(raw) == expected

    def test_to_int_defaults_to_zero(self):
        assert to_int(None) == 0
        assert to_int("abc") == 0
        assert to_int("1234.9") == 1234


class TestSMA:
    def test_window_is_null_until_full(self):
        """A 200-day average of 3 days is not a 200-day average."""
        out = market_data._sma([1.0, 2.0, 3.0], 5)
        assert out == [None, None, None]

    def test_values_align_index_for_index_with_input(self):
        closes = [float(i) for i in range(1, 11)]
        out = market_data._sma(closes, 3)
        assert len(out) == len(closes)
        assert out[0] is None and out[1] is None
        assert out[2] == pytest.approx(2.0)
        assert out[-1] == pytest.approx(9.0)

    def test_rolling_window_does_not_drift(self):
        """Guards the running-sum optimisation against accumulating error
        or failing to evict the oldest value."""
        closes = [float(i) for i in range(1, 101)]
        out = market_data._sma(closes, 10)
        for i in range(9, 100):
            expected = sum(closes[i - 9 : i + 1]) / 10
            assert out[i] == pytest.approx(expected)

    def test_gaps_reset_the_window(self):
        out = market_data._sma([1.0, 2.0, None, 4.0, 5.0], 2)
        assert out[2] is None


class TestFreshness:
    def test_recent_is_fresh(self):
        assert market_data._is_fresh(datetime.now(timezone.utc).isoformat(), 300)

    def test_old_is_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert not market_data._is_fresh(old, 300)

    def test_naive_timestamp_is_treated_as_utc(self):
        naive = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        assert market_data._is_fresh(naive, 300)

    @pytest.mark.parametrize("bad", ["", "yesterday", None, 12345])
    def test_unparseable_timestamp_is_stale_not_an_error(self, bad):
        """A corrupt cache row must cause a refetch, never a 500."""
        assert market_data._is_fresh(bad, 300) is False


class FakeProvider:
    def __init__(self, name, *, fails=None, payload=None):
        self.name = name
        self.fails = fails
        self.payload = payload or {}
        self.calls = 0

    async def search(self, query):
        self.calls += 1
        if self.fails:
            raise self.fails
        return self.payload.get("search", [])

    async def quote(self, symbol):
        self.calls += 1
        if self.fails:
            raise self.fails
        return {**self.payload.get("quote", {}), "symbol": symbol}

    async def overview(self, symbol):
        self.calls += 1
        if self.fails:
            raise self.fails
        return {**self.payload.get("overview", {}), "symbol": symbol}

    async def history(self, symbol, range_):
        self.calls += 1
        if self.fails:
            raise self.fails
        return self.payload.get("history", {})


class TestProviderFallback:
    async def test_rate_limited_provider_falls_through(self, monkeypatch, fake_sb):
        primary = FakeProvider("primary", fails=RateLimitError("429"))
        backup = FakeProvider("backup", payload={"quote": {"price": 101.0}})
        monkeypatch.setattr(
            market_data, "get_provider_chain", lambda: [primary, backup]
        )

        out = await market_data.get_quote("AAPL")
        assert out["price"] == 101.0
        assert primary.calls == 1 and backup.calls == 1

    async def test_first_healthy_provider_wins(self, monkeypatch, fake_sb):
        primary = FakeProvider("primary", payload={"quote": {"price": 50.0}})
        backup = FakeProvider("backup", payload={"quote": {"price": 99.0}})
        monkeypatch.setattr(
            market_data, "get_provider_chain", lambda: [primary, backup]
        )

        out = await market_data.get_quote("AAPL")
        assert out["price"] == 50.0
        assert backup.calls == 0, "backup should not be called when primary answers"

    async def test_all_failing_raises(self, monkeypatch, fake_sb):
        chain = [
            FakeProvider("a", fails=RateLimitError("429")),
            FakeProvider("b", fails=ProviderError("nope")),
        ]
        monkeypatch.setattr(market_data, "get_provider_chain", lambda: chain)
        with pytest.raises(ProviderError):
            await market_data.get_quote("AAPL")

    async def test_stale_cache_beats_an_error(self, monkeypatch, fake_sb):
        """When every provider is down, last-known data is more useful than
        a failed page."""
        fake_sb.store["quote_cache"] = [
            {
                "symbol": "AAPL",
                "payload": {"symbol": "AAPL", "price": 42.0},
                "fetched_at": (
                    datetime.now(timezone.utc) - timedelta(days=5)
                ).isoformat(),
            }
        ]
        monkeypatch.setattr(
            market_data,
            "get_provider_chain",
            lambda: [FakeProvider("a", fails=RateLimitError("429"))],
        )

        out = await market_data.get_quote("AAPL")
        assert out["price"] == 42.0
        assert out["stale"] is True and out["cached"] is True

    async def test_a_provider_crash_does_not_escape(self, monkeypatch, fake_sb):
        """A provider raising something unexpected must be contained, or one
        bad vendor takes the whole endpoint down."""
        class Exploding(FakeProvider):
            async def quote(self, symbol):
                raise RuntimeError("unhandled vendor bug")

        chain = [Exploding("bad"), FakeProvider("good", payload={"quote": {"price": 7.0}})]
        monkeypatch.setattr(market_data, "get_provider_chain", lambda: chain)

        out = await market_data.get_quote("AAPL")
        assert out["price"] == 7.0


class TestCacheReads:
    async def test_fresh_cache_skips_the_provider(self, monkeypatch, fake_sb):
        provider = FakeProvider("p", payload={"quote": {"price": 1.0}})
        monkeypatch.setattr(market_data, "get_provider_chain", lambda: [provider])
        fake_sb.store["quote_cache"] = [
            {
                "symbol": "AAPL",
                "payload": {"symbol": "AAPL", "price": 123.0},
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        out = await market_data.get_quote("AAPL")
        assert out["price"] == 123.0
        assert out["cached"] is True
        assert provider.calls == 0

    async def test_symbol_lookup_is_case_insensitive(self, monkeypatch, fake_sb):
        provider = FakeProvider("p", payload={"quote": {"price": 5.0}})
        monkeypatch.setattr(market_data, "get_provider_chain", lambda: [provider])
        out = await market_data.get_quote("  aapl  ")
        assert out["symbol"] == "AAPL"


class TestCurrencySymbol:
    @pytest.mark.parametrize(
        "code,sym", [("USD", "$"), ("INR", "₹"), ("inr", "₹"), ("GBP", "£")]
    )
    def test_known_currencies(self, code, sym):
        assert market_data.currency_symbol(code) == sym

    def test_unknown_currency_falls_back_to_the_code(self):
        assert market_data.currency_symbol("XYZ") == "XYZ"

    def test_missing_currency_is_empty(self):
        assert market_data.currency_symbol(None) == ""
