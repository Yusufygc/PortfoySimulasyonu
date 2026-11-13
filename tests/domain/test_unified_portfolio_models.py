"""Birleşik portföy DTO'ları: HoldingValuation, UnifiedSummary, günlük kazanç ve gram birim fiyatı."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.unified_portfolio import (
    AllocationClass,
    AllocationSlice,
    HoldingValuation,
    UnifiedSummary,
    allocation_class_for,
    daily_gain,
)
from src.domain.units import TROY_OUNCE_GRAMS

D = Decimal


def holding(symbol="X", cls=AllocationClass.CRYPTO, value="150", cost="100", **overrides) -> HoldingValuation:
    values = dict(
        key=f"{cls.value}:{symbol}", symbol=symbol, name=symbol, allocation_class=cls, quantity=D("1"),
        native_currency="USD", cost_native=D(cost), cost_try=D(cost), value_try=D(value),
    )
    values.update(overrides)
    return HoldingValuation(**values)


def summary(holdings, cash="0", daily_gain_try="0", **overrides) -> UnifiedSummary:
    cash_value = D(cash)
    total = sum((h.value_try for h in holdings), D("0")) + cash_value
    values = dict(
        holdings=tuple(holdings), cash_try=cash_value, total_value_try=total,
        total_cost_try=sum((h.cost_try for h in holdings), D("0")), daily_gain_try=D(daily_gain_try), slices=(),
    )
    values.update(overrides)
    return UnifiedSummary(**values)


class TestAllocationClass:
    def test_maps_every_asset_class(self):
        for asset_class in AssetClass:
            assert allocation_class_for(asset_class).value == asset_class.value

    def test_bist_and_cash_are_not_asset_classes(self):
        assert {c.value for c in AllocationClass} - {c.value for c in AssetClass} == {"BIST_STOCK", "CASH"}


class TestDailyGain:
    def test_gain_is_value_minus_previous_value(self):
        assert daily_gain(D("110"), D("10")) == D("10")
        assert daily_gain(D("90"), D("-10")) == D("-10")

    def test_unknown_change_is_zero(self):
        assert daily_gain(D("110"), None) == D("0")


class TestHoldingValuation:
    def test_unrealized_pl_and_pct(self):
        position = holding(value="150", cost="100")

        assert position.unrealized_pl_try == D("50")
        assert position.unrealized_pl_pct == D("50")

    def test_pct_is_none_when_cost_is_zero(self):
        assert holding(value="10", cost="0").unrealized_pl_pct is None


class TestUnifiedSummary:
    def test_totals_exclude_cash_from_pl(self):
        result = summary([holding("A", value="150", cost="100"), holding("B", value="80", cost="100")], cash="1000")

        assert result.total_value_try == D("1230")
        assert result.unrealized_pl_try == D("30")
        assert result.unrealized_pl_pct == D("15")   # 30 / 200

    def test_daily_change_pct_uses_previous_value(self):
        result = summary([holding(value="110")], daily_gain_try="10")

        assert result.daily_change_pct == D("10")     # 10 / (110 - 10)

    def test_empty_summary_has_no_percentages(self):
        result = summary([])

        assert result.unrealized_pl_pct is None and result.daily_change_pct is None
        assert not result.is_partial

    def test_partial_when_unpriced_symbols_exist(self):
        assert summary([holding()], unpriced_symbols=("X",)).is_partial

    def test_display_amount_and_holdings_filter(self):
        result = summary(
            [holding("BTC", AllocationClass.CRYPTO), holding("THY", AllocationClass.BIST_STOCK)],
            display_currency="USD", display_rate=D("0.025"),
        )

        assert result.display_amount(D("400")) == D("10")
        assert [h.symbol for h in result.holdings_of(AllocationClass.BIST_STOCK)] == ["THY"]
        assert result.holdings_of(AllocationClass.US_STOCK) == ()

    def test_slice_is_a_plain_record(self):
        assert AllocationSlice(AllocationClass.CASH, D("5"), D("50"), 0).holdings_count == 0


class TestAssetUnitPrice:
    def make(self, unit, asset_class=AssetClass.PRECIOUS_METAL):
        return Asset(1, "XAU", "Altın", asset_class, "USD", "GC=F", unit)

    def test_gram_metal_converts_ounce_quote_to_gram(self):
        assert self.make(AssetUnit.GRAM).unit_price(TROY_OUNCE_GRAMS * 100) == D("100")

    @pytest.mark.parametrize("unit", [AssetUnit.OUNCE, AssetUnit.UNIT])
    def test_other_units_keep_quote(self, unit):
        assert self.make(unit).unit_price(D("2650")) == D("2650")

    def test_non_metal_is_never_converted(self):
        assert self.make(AssetUnit.GRAM, AssetClass.CRYPTO).unit_price(D("5")) == D("5")
