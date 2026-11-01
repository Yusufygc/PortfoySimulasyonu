"""MyPortfolioController: birleşik özetin QML özelliklerine ve tablo modeline yansıması (sahte servisle)."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QModelIndex, Qt

from src.domain.models.unified_portfolio import (
    AllocationClass,
    AllocationSlice,
    HoldingValuation,
    UnifiedSummary,
)
from src.ui_qml.controllers.my_portfolio_controller import MyPortfolioController

D = Decimal


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


def holding(symbol, cls, value, cost, currency="USD", daily=None, priced=True):
    return HoldingValuation(
        key=f"{cls.value}:{symbol}", symbol=symbol, name=symbol, allocation_class=cls, quantity=D("2"),
        native_currency=currency, cost_native=D(cost), cost_try=D(cost), value_try=D(value),
        price_native=D("50"), daily_change_pct=None if daily is None else D(daily), is_priced=priced, ref_id=1,
    )


def make_summary(currency="TRY", rate="1", unavailable=False, unpriced=()):
    holdings = (
        holding("AAPL", AllocationClass.US_STOCK, "6000", "5000", daily="2"),
        holding("THYAO", AllocationClass.BIST_STOCK, "3000", "3500", currency="TRY", daily="-1"),
        holding("BTC", AllocationClass.CRYPTO, "500", "500", priced=not unpriced),
    )
    return UnifiedSummary(
        holdings=holdings, cash_try=D("500"), total_value_try=D("10000"), total_cost_try=D("9000"),
        daily_gain_try=D("120"),
        slices=(
            AllocationSlice(AllocationClass.US_STOCK, D("6000"), D("60"), 1),
            AllocationSlice(AllocationClass.BIST_STOCK, D("3000"), D("30"), 1),
            AllocationSlice(AllocationClass.CRYPTO, D("500"), D("5"), 1),
            AllocationSlice(AllocationClass.CASH, D("500"), D("5"), 0),
        ),
        unpriced_symbols=tuple(unpriced), display_currency=currency, display_rate=D(rate),
        display_unavailable=unavailable, usd_try_rate=D("40") if currency == "USD" else None,
    )


class FakeService:
    def __init__(self):
        self.calls = []
        self.fail = False

    def get_summary(self, display_currency="TRY"):
        self.calls.append(display_currency)
        if self.fail:
            raise RuntimeError("db kilitli")
        return make_summary(display_currency, "0.025" if display_currency == "USD" else "1")


@pytest.fixture
def parts(qapp):
    service = FakeService()
    return service, MyPortfolioController(container=SimpleNamespace(unified_portfolio_service=service))


def names(controller):
    model = controller.holdingsModel
    role = {bytes(v).decode(): k for k, v in model.roleNames().items()}["symbol"]
    return [model.data(model.index(i, 0), role) for i in range(model.rowCount())]


class TestSummaryProperties:
    def test_formats_kpis_in_try(self, parts):
        _, controller = parts

        assert controller.totalValue == "₺10,000.00"
        assert controller.totalCost == "₺9,000.00"
        assert controller.cashBalance == "₺500.00" and controller.cashRatio == "%5.0"
        assert controller.dailyGain == "₺120.00" and controller.isDailyPositive
        assert controller.dailyGainPct == "+%1.21"        # 120 / (10000 - 120)
        assert controller.holdingsCount == 3 and not controller.isPartial

    def test_unrealized_pl_matches_holdings(self, parts):
        _, controller = parts

        # (6000-5000) + (3000-3500) + (500-500)
        assert controller.unrealizedPL == "₺500.00"
        assert controller.unrealizedPLPct == "+%5.56"     # 500 / 9000
        assert controller.isPLPositive

    def test_allocation_slices_and_tab_counts(self, parts):
        _, controller = parts

        slices = controller.allocationSlices
        assert [s["classKey"] for s in slices] == ["US_STOCK", "BIST_STOCK", "CRYPTO", "CASH"]
        assert slices[0]["pct"] == 0.6 and slices[0]["amount"] == "₺6,000.00"
        assert controller.tabCounts == {"ALL": 3, "BIST_STOCK": 1, "US_STOCK": 1, "CRYPTO": 1, "PRECIOUS_METAL": 0}

    def test_no_container_yields_empty_page(self, qapp):
        controller = MyPortfolioController(container=None)

        assert controller.totalValue == "₺0.00" and controller.holdingsCount == 0
        assert controller.allocationSlices == [] and controller.holdingsModel.rowCount() == 0
        assert controller.dailyGainPct == "-"


class TestCurrencyAndTabs:
    def test_switching_to_usd_reloads_with_usd_and_converts(self, parts):
        service, controller = parts
        changed = []
        controller.currencyChanged.connect(lambda: changed.append(True))

        controller.setDisplayCurrency("usd")

        assert service.calls == ["TRY", "USD"]
        assert controller.displayCurrency == "USD" and controller.totalValue == "$250.00"
        assert controller.usdRate == "40.0000" and changed == [True]

    def test_unsupported_or_same_currency_is_ignored(self, parts):
        service, controller = parts

        controller.setDisplayCurrency("EUR")
        controller.setDisplayCurrency("TRY")

        assert service.calls == ["TRY"] and controller.displayCurrency == "TRY"

    def test_active_class_filters_model_without_reloading(self, parts):
        service, controller = parts

        assert names(controller) == ["AAPL", "THYAO", "BTC"]
        controller.setActiveClass("BIST_STOCK")

        assert names(controller) == ["THYAO"] and controller.activeClass == "BIST_STOCK"
        assert service.calls == ["TRY"]

    def test_unknown_tab_is_ignored(self, parts):
        _, controller = parts

        controller.setActiveClass("ETF")

        assert controller.activeClass == "ALL"

    def test_filter_survives_reload(self, parts):
        _, controller = parts
        controller.setActiveClass("CRYPTO")

        controller.reload()

        assert names(controller) == ["BTC"]


class TestFailureAndPartial:
    def test_failed_reload_keeps_previous_summary(self, parts):
        service, controller = parts
        service.fail = True

        controller.reload()

        assert controller.totalValue == "₺10,000.00" and controller.holdingsCount == 3

    def test_partial_flag_and_symbols(self, qapp):
        class Partial(FakeService):
            def get_summary(self, display_currency="TRY"):
                return make_summary(unpriced=("BTC",))

        controller = MyPortfolioController(container=SimpleNamespace(unified_portfolio_service=Partial()))

        assert controller.isPartial and controller.unpricedSymbols == ["BTC"]

    def test_display_unavailable_when_usd_rate_missing(self, qapp):
        class NoRate(FakeService):
            def get_summary(self, display_currency="TRY"):
                return make_summary("TRY", "1", unavailable=display_currency == "USD")

        controller = MyPortfolioController(container=SimpleNamespace(unified_portfolio_service=NoRate()))
        controller.setDisplayCurrency("USD")

        assert controller.displayUnavailable and controller.totalValue == "₺10,000.00"

    def test_reload_prices_alias_and_summary_signal(self, parts):
        service, controller = parts
        emitted = []
        controller.summaryChanged.connect(lambda: emitted.append(True))

        controller.reloadPrices()

        assert service.calls == ["TRY", "TRY"] and emitted == [True]
