"""PortfolioController — d1 Controller/Model Temel Katman referans controller testleri."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.qt_compat.qtcore import Qt
from src.application.services.analysis.return_calc_service import PortfolioValueSnapshot
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.ui_qml.controllers.portfolio_controller import PortfolioController


def _position(stock_id: int, quantity: int, total_cost: str) -> Position:
    position = Position(stock_id=stock_id)
    position.total_quantity = quantity
    position.total_cost = Decimal(total_cost)
    return position


def _make_container(positions, price_map, ticker_map, latest_price_map=None):
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
    container.stock_repo.get_ticker_map_for_stock_ids.return_value = ticker_map
    container.latest_price_repo.get_latest_price_map.return_value = latest_price_map or {}
    return container


class TestInitialLoad:
    def test_totals_computed_from_snapshot(self, qapp):
        positions = [_position(1, 10, "1000"), _position(2, 5, "500")]
        price_map = {1: Decimal("120"), 2: Decimal("90")}
        container = _make_container(positions, price_map, ticker_map={1: "AKBNK", 2: "THYAO"})

        controller = PortfolioController(container)

        assert controller.totalValue == 1650.0  # 10*120 + 5*90
        assert controller.totalCost == 1500.0
        assert controller.unrealizedPl == 150.0

    def test_no_positions_gives_zero_totals(self, qapp):
        container = _make_container([], {}, {})
        controller = PortfolioController(container)

        assert controller.totalValue == 0.0
        assert controller.totalCost == 0.0
        assert controller.unrealizedPl == 0.0
        assert controller.positionsModel.rowCount() == 0


class TestPositionsModel:
    def test_rows_expose_ticker_and_unrealized_pl(self, qapp):
        positions = [_position(1, 10, "1000")]
        price_map = {1: Decimal("120")}
        container = _make_container(positions, price_map, ticker_map={1: "AKBNK"})

        controller = PortfolioController(container)
        model = controller.positionsModel

        assert model.rowCount() == 1
        assert model.data(model.index(0, 0), Qt.DisplayRole) == "AKBNK"  # Hisse
        assert model.data(model.index(0, 1), Qt.DisplayRole) == 10       # Lot
        assert model.data(model.index(0, 4), Qt.DisplayRole) == 200.0    # K/Z = 1200-1000

    def test_missing_price_gives_zero_unrealized_pl_for_that_row(self, qapp):
        positions = [_position(1, 10, "1000")]
        container = _make_container(positions, price_map={}, ticker_map={1: "AKBNK"})

        controller = PortfolioController(container)
        row = controller.positionsModel.row_at(0)

        assert row["current_price"] == 0.0
        assert row["unrealized_pl"] == 0.0


class TestLatestPriceOverlay:
    def test_latest_price_takes_precedence_over_snapshot_price(self, qapp):
        positions = [_position(1, 10, "1000")]
        snapshot_price_map = {1: Decimal("100")}
        container = _make_container(
            positions, snapshot_price_map, ticker_map={1: "AKBNK"},
            latest_price_map={1: Decimal("150")},
        )

        controller = PortfolioController(container)

        assert controller.totalValue == 1500.0  # 10*150, snapshot'ın 100'ü değil


class TestRefreshAndSignals:
    def test_refresh_recomputes_after_container_data_changes(self, qapp):
        positions = [_position(1, 10, "1000")]
        container = _make_container(positions, {1: Decimal("100")}, ticker_map={1: "AKBNK"})
        controller = PortfolioController(container)
        assert controller.totalValue == 1000.0

        container.return_calc_service.compute_portfolio_value_on.return_value = PortfolioValueSnapshot(
            as_of_date=date.today(),
            total_cost=Decimal("1000"),
            total_value=Decimal("2000"),
            total_unrealized_pl=Decimal("1000"),
            total_realized_pl=Decimal("0"),
            price_map={1: Decimal("200")},
        )
        controller.refresh()

        assert controller.totalValue == 2000.0

    def test_signal_only_emitted_when_value_actually_changes(self, qapp):
        positions = [_position(1, 10, "1000")]
        container = _make_container(positions, {1: Decimal("100")}, ticker_map={1: "AKBNK"})
        controller = PortfolioController(container)

        received = []
        controller.totalValueChanged.connect(lambda: received.append(True))
        controller.refresh()  # aynı veri, değer değişmiyor

        assert received == []
