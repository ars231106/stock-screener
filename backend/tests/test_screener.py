"""The screening engine.

These are the tests that matter most: a screener that silently includes a
company it should have excluded is worse than one that crashes, because
nobody notices.
"""

from __future__ import annotations

import pytest

from app.services import screener


class TestCriteriaToSQL:
    """Criteria must become predicates, and bad input must be rejected
    loudly rather than quietly matching everything."""

    def test_unknown_metric_is_rejected(self, fake_sb):
        q = fake_sb.table("fundamentals").select("*")
        with pytest.raises(ValueError, match="Unknown metric"):
            screener._apply(q, {"metric": "profit_vibes", "op": "gt", "value": 1})

    def test_unknown_operator_is_rejected(self, fake_sb):
        q = fake_sb.table("fundamentals").select("*")
        with pytest.raises(ValueError, match="Unknown operator"):
            screener._apply(q, {"metric": "pe_ratio", "op": "approximately", "value": 1})

    def test_between_requires_an_upper_bound(self, fake_sb):
        q = fake_sb.table("fundamentals").select("*")
        with pytest.raises(ValueError, match="between"):
            screener._apply(q, {"metric": "pe_ratio", "op": "between", "value": 5})

    def test_between_orders_its_bounds(self, fake_sb):
        """A user who types the bounds backwards should still get a range,
        not an empty result."""
        q = fake_sb.table("fundamentals").select("*")
        q = screener._apply(
            q, {"metric": "pe_ratio", "op": "between", "value": 30, "value2": 10}
        )
        ops = {(op, col, val) for op, col, val in q.filters}
        assert ("gte", "pe_ratio", 10.0) in ops
        assert ("lte", "pe_ratio", 30.0) in ops

    def test_every_criterion_excludes_nulls(self, fake_sb):
        """The null guard is the whole correctness story: an unknown P/E is
        not a low P/E."""
        q = fake_sb.table("fundamentals").select("*")
        q = screener._apply(q, {"metric": "pe_ratio", "op": "lt", "value": 20})
        assert ("not.is", "pe_ratio", "null") in q.filters


class TestRunScreen:
    @pytest.fixture(autouse=True)
    def _seed(self, fake_sb, fundamentals_rows, monkeypatch):
        fake_sb.store["fundamentals"] = [dict(r) for r in fundamentals_rows]

        async def no_quote(_symbol):
            raise screener.MarketDataError("quotes disabled in tests")

        monkeypatch.setattr(screener.market_data, "get_quote", no_quote)

    async def test_excludes_rows_missing_the_metric(self, fake_sb):
        """Intel has no P/E (it is loss-making). A 'P/E under 20' screen must
        not return it -- the classic bug is treating null as 0."""
        out = await screener.run_screen(
            [{"metric": "pe_ratio", "op": "lt", "value": 20}]
        )
        symbols = {r["symbol"] for r in out["results"]}
        assert "INTC" not in symbols
        assert symbols == {"BAC", "ITC.NS"}

    async def test_criteria_are_anded(self, fake_sb):
        out = await screener.run_screen(
            [
                {"metric": "pe_ratio", "op": "lt", "value": 20},
                {"metric": "dividend_yield", "op": "gt", "value": 0.05},
            ]
        )
        assert {r["symbol"] for r in out["results"]} == {"ITC.NS"}

    async def test_null_metric_excluded_even_when_other_criteria_pass(self, fake_sb):
        """ITC passes on P/E but has no ROE, so an ROE criterion must drop
        it rather than let the earlier match carry it through."""
        out = await screener.run_screen(
            [
                {"metric": "pe_ratio", "op": "lt", "value": 20},
                {"metric": "roe", "op": "gt", "value": 0.05},
            ]
        )
        assert {r["symbol"] for r in out["results"]} == {"BAC"}

    async def test_matched_is_the_total_not_the_page(self, fake_sb):
        """The regression this suite exists to prevent: `matched` once
        reported the page size, so a truncated result looked complete."""
        out = await screener.run_screen(
            [{"metric": "market_cap", "op": "gt", "value": 1}], limit=2
        )
        assert out["matched"] == 4
        assert out["returned"] == 2
        assert out["truncated"] is True
        assert len(out["results"]) == 2

    async def test_not_truncated_when_everything_fits(self, fake_sb):
        out = await screener.run_screen(
            [{"metric": "market_cap", "op": "gt", "value": 1}], limit=50
        )
        assert out["matched"] == out["returned"] == 4
        assert out["truncated"] is False

    async def test_empty_table_reports_partial_not_zero_matches(self, fake_sb):
        """Before the refresh job has run, 'no data yet' must not be
        presented as 'nothing passes your criteria'."""
        fake_sb.store["fundamentals"] = []
        out = await screener.run_screen(
            [{"metric": "pe_ratio", "op": "lt", "value": 20}]
        )
        assert out["partial"] is True
        assert out["matched"] == 0
        assert "refresh" in (out["message"] or "").lower()

    async def test_bad_metric_returns_a_message_not_an_exception(self, fake_sb):
        out = await screener.run_screen([{"metric": "nope", "op": "gt", "value": 1}])
        assert out["results"] == []
        assert "Unknown metric" in (out["message"] or "")

    async def test_quote_failure_does_not_drop_the_row(self, fake_sb):
        """Price is decoration on a screen row; losing it must not lose the
        company."""
        out = await screener.run_screen(
            [{"metric": "pe_ratio", "op": "lt", "value": 20}]
        )
        assert len(out["results"]) == 2
        assert all(r["price"] is None for r in out["results"])

    async def test_results_are_deterministically_ordered(self, fake_sb):
        out = await screener.run_screen(
            [{"metric": "market_cap", "op": "gt", "value": 1}]
        )
        symbols = [r["symbol"] for r in out["results"]]
        assert symbols == sorted(symbols)


class TestPresets:
    def test_every_preset_uses_known_metrics_and_operators(self):
        """A typo in a preset would surface as 'no matches' rather than an
        error, so it is checked here instead."""
        for key, preset in screener.PRESET_SCREENS.items():
            assert preset["criteria"], f"{key} has no criteria"
            for c in preset["criteria"]:
                assert c["metric"] in screener.METRICS, f"{key}: {c['metric']}"
                assert c["op"] in {"gt", "gte", "lt", "lte", "eq", "between"}

    def test_percentage_presets_use_decimal_fractions(self):
        """Ratios are stored as decimals (0.15 = 15%). A preset written as
        15 would match nothing, silently."""
        for key, preset in screener.PRESET_SCREENS.items():
            for c in preset["criteria"]:
                if screener.METRICS[c["metric"]]["unit"] == "pct":
                    assert abs(c["value"]) < 2, f"{key}: {c['metric']}={c['value']}"
