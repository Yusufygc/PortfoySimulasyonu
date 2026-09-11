"""DashboardView.qml — gerçek DashboardController ile uçtan uca yükleme testi
(bkz. §7.3 madde 1, d2) + §7.5 UX Polish regresyonları (rolling number + tablo
hover deseni).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.models import AllocationRiskDTO, AnalysisOverviewDTO
from src.application.services.analysis.return_calc_service import PortfolioValueSnapshot
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.donut_chart_item import DonutChartItem
from src.ui_qml.controllers.dashboard_controller import DashboardController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "DashboardView.qml"

_types_registered = False


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(DonutChartItem, "PortfoyCharts", 1, 0, "DonutChartItem")
        _types_registered = True


def _make_container() -> MagicMock:
    position = Position(stock_id=1)
    position.total_quantity = 10
    position.total_cost = Decimal("1000")
    portfolio = Portfolio(positions={1: position})
    price_map = {1: Decimal("120")}

    container = MagicMock()
    container.portfolio_service.get_current_portfolio.return_value = portfolio
    container.return_calc_service.compute_portfolio_value_on.return_value = PortfolioValueSnapshot(
        as_of_date=date.today(),
        total_cost=Decimal("1000"),
        total_value=portfolio.total_market_value(price_map),
        total_unrealized_pl=portfolio.total_unrealized_pl(price_map),
        total_realized_pl=Decimal("0"),
        price_map=price_map,
    )
    container.return_calc_service.compute_return_between.return_value = (Decimal("0.01"), None, None)
    container.stock_repo.get_ticker_map_for_stock_ids.return_value = {1: "AKBNK"}
    container.latest_price_repo.get_latest_price_map.return_value = {}
    container.portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)
    container.portfolio_analytics_service.get_overview.return_value = AnalysisOverviewDTO(
        total_value=Decimal("1200"), period_return_pct=12.5, benchmark_gap_pct=3.2, benchmark_label="BIST 100",
        largest_position_label="AKBNK", largest_position_weight_pct=100.0, best_contributor_label="AKBNK",
        best_contributor_pct=12.5, worst_contributor_label="-", worst_contributor_pct=None, max_drawdown_pct=-5.0,
        insights=[], warnings=[], portfolio_label="Ana Portföy",
    )
    container.portfolio_analytics_service.get_allocation_risk_view.return_value = AllocationRiskDTO(
        items=[], top_three_weight_pct=100.0, volatility_pct=10.0, max_drawdown_pct=-5.0,
        concentration_label="Yüksek", warnings=[], sharpe_ratio=1.5,
    )
    return container


@pytest.fixture
def loaded_engine(qapp):
    _ensure_types_registered()
    controller = DashboardController(_make_container())

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("dashboardController", controller)
    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"DashboardView.qml bulunamadı: {_QML_FILE}"


def test_loads_without_warnings(loaded_engine):
    engine, _controller, warnings_seen = loaded_engine
    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"


class TestRollingNumberPolish:
    def test_animated_total_value_matches_controller_on_initial_load(self, loaded_engine):
        # Behavior yalnızca SONRAKİ değişimleri animasyonlar — ilk binding anında
        # (component tamamlanır tamamlanmaz) değer zaten gerçek değere eşit olmalı.
        engine, controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        assert root.property("animatedTotalValue") == pytest.approx(controller.portfolio.totalValue)

    def test_animated_unrealized_pl_matches_controller_on_initial_load(self, loaded_engine):
        engine, controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        assert root.property("animatedUnrealizedPl") == pytest.approx(controller.portfolio.unrealizedPl)
