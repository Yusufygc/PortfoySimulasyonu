"""DashboardController — d2 Dashboard KPI/tablo/donut köprüsü testleri."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.analysis.models import AllocationRiskDTO, AnalysisOverviewDTO
from src.application.services.analysis.return_calc_service import PortfolioValueSnapshot
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.ui_qml.controllers.dashboard_controller import DashboardController


def _position(stock_id: int, quantity: int, total_cost: str) -> Position:
    position = Position(stock_id=stock_id)
    position.total_quantity = quantity
    position.total_cost = Decimal(total_cost)
    return position


def _overview(period_return_pct=12.5, benchmark_gap_pct=3.2, benchmark_label="BIST 100") -> AnalysisOverviewDTO:
    return AnalysisOverviewDTO(
        total_value=Decimal("1000"),
        period_return_pct=period_return_pct,
        benchmark_gap_pct=benchmark_gap_pct,
        benchmark_label=benchmark_label,
        largest_position_label="AKBNK",
        largest_position_weight_pct=60.0,
        best_contributor_label="AKBNK",
        best_contributor_pct=12.5,
        worst_contributor_label="-",
        worst_contributor_pct=None,
        max_drawdown_pct=-8.0,
        insights=[],
        warnings=[],
        portfolio_label="Ana Portföy",
    )


def _risk_view(sharpe_ratio=1.92) -> AllocationRiskDTO:
    return AllocationRiskDTO(
        items=[],
        top_three_weight_pct=100.0,
        volatility_pct=15.0,
        max_drawdown_pct=-8.0,
        concentration_label="Yüksek",
        warnings=[],
        sharpe_ratio=sharpe_ratio,
    )


def _make_container(
    positions,
    price_map,
    ticker_map,
    overview=None,
    risk_view=None,
    daily_return_rate=Decimal("0.0234"),
):
    container = MagicMock()
    portfolio = Portfolio(positions={p.stock_id: p for p in positions})
    container.portfolio_service.get_current_portfolio.return_value = portfolio
    container.return_calc_service.compute_portfolio_value_on.return_value = PortfolioValueSnapshot(
        as_of_date=date.today(),
        total_cost=sum((p.total_cost for p in positions), Decimal("0")),
        total_value=portfolio.total_market_value(price_map),
        total_unrealized_pl=portfolio.total_unrealized_pl(price_map),
        total_realized_pl=Decimal("0"),
        price_map=price_map,
    )
    container.return_calc_service.compute_return_between.return_value = (daily_return_rate, None, None)
    container.stock_repo.get_ticker_map_for_stock_ids.return_value = ticker_map
    container.latest_price_repo.get_latest_price_map.return_value = {}
    container.portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)
    container.portfolio_analytics_service.get_overview.return_value = overview or _overview()
    container.portfolio_analytics_service.get_allocation_risk_view.return_value = risk_view or _risk_view()
    return container


class TestKpiProperties:
    def test_daily_change_pct_from_return_calc_service(self, qapp):
        container = _make_container([], {}, {}, daily_return_rate=Decimal("0.0234"))
        controller = DashboardController(container)
        assert controller.dailyChangePct == 2.34

    def test_total_return_and_benchmark_gap_from_overview(self, qapp):
        container = _make_container([], {}, {}, overview=_overview(period_return_pct=29.8, benchmark_gap_pct=8.4, benchmark_label="BIST 100"))
        controller = DashboardController(container)

        assert controller.totalReturnPct == 29.8
        assert controller.benchmarkGapPct == 8.4
        assert controller.benchmarkLabel == "BIST 100"

    def test_sharpe_ratio_from_allocation_risk_view(self, qapp):
        container = _make_container([], {}, {}, risk_view=_risk_view(sharpe_ratio=1.92))
        controller = DashboardController(container)
        assert controller.sharpeRatio == 1.92

    def test_none_metrics_default_to_zero(self, qapp):
        container = _make_container(
            [], {}, {},
            overview=_overview(period_return_pct=None, benchmark_gap_pct=None, benchmark_label=None),
            risk_view=_risk_view(sharpe_ratio=None),
        )
        controller = DashboardController(container)

        assert controller.totalReturnPct == 0.0
        assert controller.benchmarkGapPct == 0.0
        assert controller.benchmarkLabel == ""
        assert controller.sharpeRatio == 0.0


class TestPortfolioDelegation:
    def test_portfolio_subcontroller_reflects_same_positions(self, qapp):
        positions = [_position(1, 10, "1000")]
        price_map = {1: Decimal("120")}
        container = _make_container(positions, price_map, ticker_map={1: "AKBNK"})

        controller = DashboardController(container)

        assert controller.portfolio.totalValue == 1200.0
        assert controller.portfolio.positionsModel.rowCount() == 1


class TestAllocation:
    def test_allocation_labels_and_weights_derived_from_positions(self, qapp):
        positions = [_position(1, 10, "1000"), _position(2, 5, "500")]
        price_map = {1: Decimal("120"), 2: Decimal("80")}
        container = _make_container(positions, price_map, ticker_map={1: "AKBNK", 2: "THYAO"})

        controller = DashboardController(container)

        assert controller.allocationLabels == ["AKBNK", "THYAO"]
        total = 10 * 120 + 5 * 80
        assert controller.allocationWeights[0] == (1200 / total) * 100
        assert controller.allocationWeights[1] == (400 / total) * 100

    def test_empty_portfolio_gives_empty_allocation(self, qapp):
        container = _make_container([], {}, {})
        controller = DashboardController(container)
        assert controller.allocationLabels == []
        assert controller.allocationWeights == []


class TestRefresh:
    def test_refresh_recomputes_kpis(self, qapp):
        container = _make_container([], {}, {}, overview=_overview(period_return_pct=10.0))
        controller = DashboardController(container)
        assert controller.totalReturnPct == 10.0

        container.portfolio_analytics_service.get_overview.return_value = _overview(period_return_pct=20.0)
        controller.refresh()

        assert controller.totalReturnPct == 20.0
