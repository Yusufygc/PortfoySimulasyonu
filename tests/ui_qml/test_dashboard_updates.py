"""Dashboard: kapanış fiyatı güncelleme, dönemsel getiriler ve son güncelleme bilgisi."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication

from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.last_update_store import LastUpdateStore, format_last_update, format_return_pct


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def _container(weekly=Decimal("0.0123"), monthly=Decimal("-0.05"), coordinator=None):
    container = MagicMock()
    container.portfolio_service.get_current_portfolio.return_value = SimpleNamespace(active_positions={})
    container.portfolio_service.get_cash_balance.return_value = Decimal("1000")
    container.return_calc_service.compute_weekly_return.return_value = (weekly, None, None)
    container.return_calc_service.compute_monthly_return.return_value = (monthly, None, None)
    if coordinator is not None:
        container.update_coordinator = coordinator
    return container


def _controller(container):
    ctrl = DashboardController(container=container)
    ctrl._executor = ImmediateExecutor()
    return ctrl


def test_formatters():
    assert format_return_pct(None) == "-" and format_return_pct(1.234) == "%+1,23" and format_return_pct(-0.5) == "%-0,50"
    assert format_last_update(None) == ""
    assert format_last_update(datetime(2026, 10, 3, 14, 5)) == "Son güncelleme: 03.10.2026 14:05"


def test_store_roundtrip_matches_legacy_keys(qapp):
    store = LastUpdateStore()
    assert store.dashboard_last_update() is None and store.saved_returns() == (None, None)

    moment = store.save_dashboard_last_update(datetime(2026, 10, 3, 9, 30, 45))
    store.save_model_portfolio_last_update(7, datetime(2026, 10, 2, 18, 0))
    store.save_returns(1.5, None)

    assert store.dashboard_last_update() == moment
    assert store.model_portfolio_last_update(7) == datetime(2026, 10, 2, 18, 0) and store.model_portfolio_last_update(8) is None
    assert store.saved_returns() == (1.5, None)


def test_returns_are_computed_saved_and_shown(qapp):
    ctrl = _controller(_container())
    ctrl._reload_returns()
    QCoreApplication.processEvents()

    assert ctrl.weeklyReturnText == "%+1,23" and ctrl.isWeeklyPositive is True
    assert ctrl.monthlyReturnText == "%-5,00" and ctrl.isMonthlyPositive is False
    weekly, monthly = LastUpdateStore().saved_returns()
    assert round(weekly, 2) == 1.23 and round(monthly, 2) == -5.0


def test_saved_returns_are_shown_before_recomputation(qapp):
    LastUpdateStore().save_returns(2.0, 3.0)

    ctrl = DashboardController(container=None)

    assert ctrl.weeklyReturnText == "%+2,00" and ctrl.monthlyReturnText == "%+3,00"


def test_return_calculation_failure_keeps_previous_values(qapp):
    container = _container()
    container.return_calc_service.compute_weekly_return.side_effect = RuntimeError("fiyat yok")
    ctrl = _controller(container)
    ctrl._weekly_pct, ctrl._monthly_pct = 4.0, 5.0

    ctrl._reload_returns()
    QCoreApplication.processEvents()

    assert ctrl.weeklyReturnText == "%+4,00"


def test_update_closing_prices_success_records_time_and_notifies(qapp):
    coordinator = MagicMock()
    coordinator.update_today_prices_and_get_snapshot.return_value = (SimpleNamespace(updated_count=3), object())
    ctrl = _controller(_container(coordinator=coordinator))
    results = _capture(ctrl.closingPricesUpdated)
    states = _capture(ctrl.priceUpdateStateChanged)

    ctrl.updateClosingPrices()
    QCoreApplication.processEvents()

    assert results == [(True, "3 hissenin tarihsel kapanış verisi güncellendi.")]
    assert states == [(True,), (False,)] and ctrl.isUpdatingPrices is False
    assert ctrl.lastUpdateText.startswith("Son güncelleme: ")
    assert LastUpdateStore().dashboard_last_update() is not None


def test_update_closing_prices_without_updates_shows_reason_and_keeps_last_update(qapp):
    coordinator = MagicMock()
    coordinator.update_today_prices_and_get_snapshot.return_value = (
        SimpleNamespace(updated_count=0, skipped_reason="Piyasa kapalı"), object())
    ctrl = _controller(_container(coordinator=coordinator))
    results = _capture(ctrl.closingPricesUpdated)

    ctrl.updateClosingPrices()
    QCoreApplication.processEvents()

    assert results == [(False, "Piyasa kapalı")] and ctrl.lastUpdateText == ""


def test_update_closing_prices_error_and_missing_service(qapp):
    coordinator = MagicMock()
    coordinator.update_today_prices_and_get_snapshot.side_effect = RuntimeError("ağ yok")
    ctrl = _controller(_container(coordinator=coordinator))
    results = _capture(ctrl.closingPricesUpdated)

    ctrl.updateClosingPrices()
    QCoreApplication.processEvents()
    assert results == [(False, "Fiyat güncelleme hatası: ağ yok")] and ctrl.isUpdatingPrices is False

    offline = DashboardController(container=None)
    results = _capture(offline.closingPricesUpdated)
    offline.updateClosingPrices()
    assert results == [(False, "Fiyat güncelleme servisi bulunamadı.")]


def test_live_refresh_records_last_update_only_when_prices_changed(qapp):
    ctrl = _controller(_container())

    ctrl._live_updated_count = 0
    ctrl._on_refresh_finished()
    assert ctrl.lastUpdateText == ""

    ctrl._live_updated_count = 2
    ctrl._on_refresh_finished()
    assert ctrl.lastUpdateText.startswith("Son güncelleme: ")
