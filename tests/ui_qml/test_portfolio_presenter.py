"""Portföyüm sunum yardımcıları: biçimlendirme, satır ve dilim sözlükleri, sekme süzgeci."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.models.unified_portfolio import (
    AllocationClass,
    AllocationSlice,
    HoldingValuation,
    UnifiedSummary,
)
from src.ui_qml.presenters.portfolio_presenter import (
    CLASS_COLORS,
    TAB_ALL,
    filter_rows,
    format_money,
    format_pct,
    format_price,
    format_quantity,
    holding_row,
    slice_dict,
    tab_counts,
)

D = Decimal


def make_holding(symbol, cls, value, cost, **options):
    """Seçenekler: quantity, currency, daily, priced, ref_id, weight."""
    quantity, currency, daily = options.get("quantity", "2"), options.get("currency", "USD"), options.get("daily")
    priced, ref_id, weight = options.get("priced", True), options.get("ref_id", 7), options.get("weight", "10")
    return HoldingValuation(
        key=f"{cls.value}:{symbol}", symbol=symbol, name=f"{symbol} adı", allocation_class=cls, quantity=D(quantity),
        native_currency=currency, cost_native=D(cost) / 40, cost_try=D(cost), value_try=D(value),
        price_native=D("50"), daily_change_pct=None if daily is None else D(daily), weight_pct=D(weight),
        is_priced=priced, ref_id=ref_id,
    )


def make_summary(holdings, **overrides):
    values = dict(
        holdings=tuple(holdings), cash_try=D("0"), total_value_try=sum((h.value_try for h in holdings), D("0")),
        total_cost_try=sum((h.cost_try for h in holdings), D("0")), daily_gain_try=D("0"), slices=(),
    )
    values.update(overrides)
    return UnifiedSummary(**values)


class TestFormatting:
    @pytest.mark.parametrize(
        "amount,currency,expected",
        [
            (D("1234.5"), "TRY", "₺1.234,50"),
            (D("-13780.404"), "try", "-₺13.780,40"),
            (D("1234.5"), "USD", "$1.234,50"),
            (D("10"), "GBP", "10,00 GBP"),
        ],
    )
    def test_format_money(self, amount, currency, expected):
        assert format_money(amount, currency) == expected

    @pytest.mark.parametrize(
        "amount,currency,expected",
        [
            (D("65432.1"), "USD", "$65.432,10"),
            (D("0.5"), "USD", "$0,5000"),
            (D("0.00001234"), "USD", "$0,00001234"),
            (None, "USD", "-"),
        ],
    )
    def test_format_price_adapts_decimals_to_magnitude(self, amount, currency, expected):
        assert format_price(amount, currency) == expected

    @pytest.mark.parametrize(
        "quantity,expected",
        [(D("1250"), "1.250"), (D("0.5"), "0,5"), (D("0.12345678"), "0,12345678"), (D("3.10"), "3,1"), (D("0"), "0")],
    )
    def test_format_quantity(self, quantity, expected):
        assert format_quantity(quantity) == expected

    @pytest.mark.parametrize("value,expected", [(D("2.151"), "+%2,15"), (D("-1.2"), "-%1,20"), (D("0"), "%0,00"), (None, "-")])
    def test_format_pct(self, value, expected):
        assert format_pct(value) == expected


class TestHoldingRow:
    def test_amounts_use_display_currency_and_price_uses_native(self):
        holding = make_holding("BTC", AllocationClass.CRYPTO, value="4000", cost="3000", daily="2.5")
        summary = make_summary([holding], display_currency="USD", display_rate=D("0.025"))

        row = holding_row(holding, summary)

        assert row["value"] == "$100,00" and row["pl"] == "$25,00"
        assert row["price"] == "$50,00" and row["avgCost"] == "$37,50"   # 75 USD maliyet / 2
        assert (row["plPct"], row["dailyChange"], row["isDailyUp"], row["isUp"]) == ("+%33,33", "+%2,50", True, True)
        assert row["classKey"] == "CRYPTO" and not row["isBist"] and row["refId"] == 7
        assert row["weight"] == "%10,0"

    def test_bist_row_and_loss(self):
        holding = make_holding("THYAO", AllocationClass.BIST_STOCK, value="900", cost="1000", currency="TRY", daily="-1")

        row = holding_row(holding, make_summary([holding]))

        assert row["isBist"] and row["value"] == "₺900,00" and row["pl"] == "-₺100,00"
        assert (row["isUp"], row["isDailyUp"], row["plPct"]) == (False, False, "-%10,00")

    def test_unknown_daily_change_and_unpriced_flag(self):
        holding = make_holding("X", AllocationClass.CRYPTO, "100", "100", daily=None, priced=False, ref_id=None)

        row = holding_row(holding, make_summary([holding]))

        assert row["dailyChange"] == "-" and not row["isDailyUp"] and not row["isPriced"] and row["refId"] == 0


class TestSlicesAndTabs:
    @pytest.fixture
    def summary(self):
        holdings = [
            make_holding("AAPL", AllocationClass.US_STOCK, "300", "200"),
            make_holding("THYAO", AllocationClass.BIST_STOCK, "200", "150", currency="TRY"),
            make_holding("BTC", AllocationClass.CRYPTO, "100", "80"),
        ]
        return make_summary(holdings, cash_try=D("0"))

    def test_slice_dict_uses_fixed_class_color_and_unit_fraction(self):
        item = AllocationSlice(AllocationClass.CRYPTO, D("4000"), D("40"), 2)
        summary = make_summary([], display_currency="USD", display_rate=D("0.025"))

        result = slice_dict(item, summary)

        assert result == {"classKey": "CRYPTO", "pct": 0.4, "color": CLASS_COLORS[AllocationClass.CRYPTO], "amount": "$100,00", "count": 2}

    def test_every_class_has_a_color(self):
        assert set(CLASS_COLORS) == set(AllocationClass)

    def test_filter_rows_by_tab(self, summary):
        assert [r["symbol"] for r in filter_rows(summary, TAB_ALL)] == ["AAPL", "THYAO", "BTC"]
        assert [r["symbol"] for r in filter_rows(summary, "BIST_STOCK")] == ["THYAO"]
        assert filter_rows(summary, "PRECIOUS_METAL") == []

    def test_tab_counts(self, summary):
        assert tab_counts(summary) == {"ALL": 3, "BIST_STOCK": 1, "US_STOCK": 1, "CRYPTO": 1, "PRECIOUS_METAL": 0}
