"""Dashboard ve Model Portföy: dönemsel getiriler, ortak son güncelleme bilgisi ve fiyat değişikliğinde DB'den yeniden okuma."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication

from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.last_update_store import LastUpdateStore, format_last_update, format_return_pct


_REAL_RELOAD_RETURNS = DashboardController._reload_returns  # conftest bu metodu varsayılan olarak devre dışı bırakır


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _container(weekly=Decimal("0.0123"), monthly=Decimal("-0.05")):
    container = MagicMock()
    container.portfolio_service.get_current_portfolio.return_value = SimpleNamespace(active_positions={})
    container.portfolio_service.get_cash_balance.return_value = Decimal("1000")
    container.return_calc_service.compute_weekly_return.return_value = (weekly, None, None)
    container.return_calc_service.compute_monthly_return.return_value = (monthly, None, None)
    return container


def _controller(container):
    ctrl = DashboardController(container=container)
    ctrl._executor = ImmediateExecutor()
    ctrl._reload_returns = lambda: _REAL_RELOAD_RETURNS(ctrl)
    return ctrl


def test_formatters():
    assert format_return_pct(None) == "-" and format_return_pct(1.234) == "%+1,23" and format_return_pct(-0.5) == "%-0,50"
    assert format_last_update(None) == ""
    assert format_last_update(datetime(2026, 10, 3, 14, 5)) == "Son güncelleme: 03.10.2026 14:05"


def test_store_roundtrip_uses_shared_prices_key(qapp):
    store = LastUpdateStore()
    assert store.prices_last_update() is None and store.saved_returns() == (None, None)

    moment = store.save_prices_last_update(datetime(2026, 10, 3, 9, 30, 45))
    store.save_returns(1.5, None)

    assert store.prices_last_update() == moment
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


def test_dashboard_reload_prices_rereads_db_and_returns_without_network(qapp):
    container = _container()
    ctrl = _controller(container)
    container.portfolio_service.get_current_portfolio.reset_mock()
    container.return_calc_service.compute_weekly_return.reset_mock()

    ctrl.reloadPrices()

    container.portfolio_service.get_current_portfolio.assert_called_once()
    container.return_calc_service.compute_weekly_return.assert_called_once()
    container.live_price_refresh_service.refresh_active_prices.assert_not_called()


# ---------------------------------------------------------------------------
# Model portföy: fiyat değişikliğinde seçili portföyün fiyat haritası yeniden okunur
# ---------------------------------------------------------------------------

def _model_controller(prices):
    from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController

    service = MagicMock()
    service.get_positions.return_value = {5: object()}
    service.get_portfolio_by_id.return_value = SimpleNamespace(id=7, name="Deneme", description="")
    service.get_all_portfolios.return_value = [SimpleNamespace(id=7, name="Deneme", description="")]
    service.get_active_position_count.return_value = 1
    service.get_positions_with_details.return_value = []
    service.get_portfolio_summary.return_value = {}
    resolver = MagicMock()
    resolver.price_map.side_effect = lambda ids: dict(prices)
    live = MagicMock()
    container = SimpleNamespace(model_portfolio_service=service, current_price_resolver=resolver,
                                live_price_refresh_service=live, event_bus=None)
    ctrl = ModelPortfolioController(container=container)
    ctrl.selectPortfolio(7)
    return ctrl, prices, live


def test_model_reload_prices_rereads_price_map_without_network(qapp):
    ctrl, prices, live = _model_controller({5: Decimal("10")})
    assert ctrl._current_price_map == {5: Decimal("10")}

    prices[5] = Decimal("11")
    ctrl.reloadPrices()

    assert ctrl._current_price_map == {5: Decimal("11")}
    live.refresh_active_prices.assert_not_called()


def test_model_refresh_data_with_same_selection_rereads_prices(qapp):
    """Eskiden seçim değişmediyse önbellekteki eski fiyatla çiziliyordu (senkron sonrası eski fiyat)."""
    ctrl, prices, _ = _model_controller({5: Decimal("10")})

    prices[5] = Decimal("12")
    ctrl.refreshData()

    assert ctrl._current_price_map == {5: Decimal("12")}
