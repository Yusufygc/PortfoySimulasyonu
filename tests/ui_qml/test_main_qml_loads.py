"""Main.qml — d2 DashboardView'ün gerçek DashboardController ile uçtan uca yüklenmesi.

`visible: false` varsayılanı sayesinde pencere AÇILMAZ (bkz. Main.qml yorumu) —
headless güvenlidir. Doğrulanan: `import QtQuick.Controls` + `ApplicationWindow` +
`import "views"` (DashboardView) + `TableView`/`DonutChartItem` + context property
(`dashboardController`) binding hatasız çalışıyor.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import pandas as pd

from src.application.services.analysis.models import AllocationRiskDTO, AnalysisOverviewDTO, ComparisonViewDTO
from src.application.services.analysis.portfolio_analytics_service import ChartPanelsDTO, ExtendedRiskMetricsDTO
from src.application.services.analysis.return_calc_service import PortfolioValueSnapshot
from src.application.services.planning.risk_optimization_bridge_service import RiskAwareOptimizationResult
from src.domain.models.optimization_result import OptimizationMetrics, OptimizationResult
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.models.risk_profile import RiskLabel
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.bar_chart_item import BarChartItem
from src.ui_qml.charts.candlestick_chart_item import CandlestickChartItem
from src.ui_qml.charts.donut_chart_item import DonutChartItem
from src.ui_qml.charts.line_chart_item import LineChartItem
from src.ui_qml.charts.scatter_chart_item import ScatterChartItem
from src.ui_qml.charts.treemap_chart_item import TreemapChartItem
from src.domain.models.budget import Budget
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.analytics_controller import AnalyticsController
from src.ui_qml.controllers.cashflow_controller import CashflowController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.simulation_controller import SimulationController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.watchlist_controller import WatchlistController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "Main.qml"

_types_registered = False


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
        qmlRegisterType(DonutChartItem, "PortfoyCharts", 1, 0, "DonutChartItem")
        qmlRegisterType(CandlestickChartItem, "PortfoyCharts", 1, 0, "CandlestickChartItem")
        qmlRegisterType(BarChartItem, "PortfoyCharts", 1, 0, "BarChartItem")
        qmlRegisterType(ScatterChartItem, "PortfoyCharts", 1, 0, "ScatterChartItem")
        qmlRegisterType(TreemapChartItem, "PortfoyCharts", 1, 0, "TreemapChartItem")
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
        total_value=Decimal("1200"),
        period_return_pct=12.5,
        benchmark_gap_pct=3.2,
        benchmark_label="BIST 100",
        largest_position_label="AKBNK",
        largest_position_weight_pct=100.0,
        best_contributor_label="AKBNK",
        best_contributor_pct=12.5,
        worst_contributor_label="-",
        worst_contributor_pct=None,
        max_drawdown_pct=-5.0,
        insights=[],
        warnings=[],
        portfolio_label="Ana Portföy",
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
    # Stock360View, Main.qml'in `Component{}` bloğunda referans edildiği için QML
    # engine onu compile-time'da resolve eder — Loader tembel olsa da context
    # property'nin var olması gerekir (bkz. Stock360Controller'ın kendi testleri).
    stock_360_controller = Stock360Controller(MagicMock())

    screener_container = MagicMock()
    screener_container.screener_service.scan.return_value = []
    screener_controller = ScreenerController(screener_container)

    watchlist_container = MagicMock()
    watchlist_container.watchlist_service.get_all_watchlists.return_value = []
    watchlist_controller = WatchlistController(watchlist_container)

    analytics_container = MagicMock()
    analytics_container.portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)
    empty_df = pd.DataFrame()
    analytics_container.portfolio_analytics_service.get_chart_panels.return_value = ChartPanelsDTO(
        aligned_series=empty_df, drawdowns=empty_df, periodic_returns=empty_df,
        risk_return_metrics={},
        comparison=ComparisonViewDTO(
            portfolio_series={}, benchmark_series=[], stock_series={}, comparison_metrics=[],
            comparison_portfolios=[], current_portfolio_label="Ana Portföy", warnings=[],
        ),
    )
    analytics_container.portfolio_analytics_service.get_extended_risk_metrics.return_value = ExtendedRiskMetricsDTO(
        sharpe_ratio=None, sortino_ratio=None, calmar_ratio=None, omega_ratio=None,
        value_at_risk_95_pct=None, conditional_var_95_pct=None, beta=None, alpha=None,
        r_squared=None, tracking_error_pct=None, monthly_returns_matrix={}, benchmark_label=None,
    )
    analytics_controller = AnalyticsController(analytics_container)

    optimization_container = MagicMock()
    optimization_container.risk_optimization_bridge_service.get_active_risk_profile.return_value = None
    optimization_container.optimization_service.get_model_portfolios.return_value = []
    optimization_result = OptimizationResult(
        current_metrics=OptimizationMetrics(expected_return=0.10, volatility=0.25, sharpe_ratio=0.40),
        optimized_metrics=OptimizationMetrics(expected_return=0.18, volatility=0.22, sharpe_ratio=0.82),
        suggestions=[],
        min_volatility_metrics=OptimizationMetrics(expected_return=0.08, volatility=0.15, sharpe_ratio=0.53),
    )
    optimization_outcome = RiskAwareOptimizationResult(
        result=optimization_result, risk_label=RiskLabel.DENGELI, max_single_weight_pct=20.0,
        equity_ceiling_pct=30, used_default_profile=True, is_manual_override=False,
    )
    optimization_container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.return_value = optimization_outcome
    optimization_controller = OptimizationController(optimization_container)

    simulation_controller = SimulationController(MagicMock())

    cashflow_container = MagicMock()
    cashflow_container.planning_service.get_budget_for_month.return_value = None
    cashflow_container.planning_service.get_budget_draft_from_pinned_items.return_value = Budget(
        id=None, month="2026-09", savings_target=Decimal("0"), items=[],
    )
    cashflow_container.planning_service.get_pinned_budget_items.return_value = []
    cashflow_container.planning_service.get_all_goals.return_value = []
    cashflow_container.cash_movement_service.get_movements.return_value = []
    cashflow_container.cash_movement_service.get_cash_balance.return_value = Decimal("0")
    cashflow_controller = CashflowController(cashflow_container)

    ai_advisor_container = MagicMock()
    ai_advisor_container.settings.ai.gemini_api_key = None
    ai_advisor_container.ai_advisor_service.tool_declarations = []
    ai_advisor_container.ai_advisor_service.call_tool = MagicMock()
    ai_advisor_controller = AiAdvisorController(ai_advisor_container)

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("dashboardController", controller)
    engine.rootContext().setContextProperty("stock360Controller", stock_360_controller)
    engine.rootContext().setContextProperty("screenerController", screener_controller)
    engine.rootContext().setContextProperty("watchlistController", watchlist_controller)
    engine.rootContext().setContextProperty("analyticsController", analytics_controller)
    engine.rootContext().setContextProperty("optimizationController", optimization_controller)
    engine.rootContext().setContextProperty("simulationController", simulation_controller)
    engine.rootContext().setContextProperty("cashflowController", cashflow_controller)
    engine.rootContext().setContextProperty("aiAdvisorController", ai_advisor_controller)

    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"Main.qml bulunamadı: {_QML_FILE}"


def test_loads_without_warnings_and_creates_root_window(loaded_engine):
    engine, _controller, warnings_seen = loaded_engine

    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"


def test_root_window_stays_hidden_by_default(loaded_engine):
    engine, _controller, _warnings = loaded_engine
    root = engine.rootObjects()[0]

    assert root.property("visible") is False
