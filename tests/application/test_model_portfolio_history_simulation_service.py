from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.reporting.daily_history_models import PortfolioStatus
from src.application.services.simulation.model_portfolio_history_simulation_service import (
    ModelPortfolioHistorySimulationService,
)
from src.domain.models.model_portfolio import ModelPortfolioTrade, ModelTradeSide
from src.domain.models.stock import Stock


class FakeModelPortfolioRepo:
    def get_trades_by_portfolio_id(self, portfolio_id):
        return [
            ModelPortfolioTrade(
                id=1,
                portfolio_id=portfolio_id,
                stock_id=10,
                trade_date=date(2026, 5, 25),
                trade_time=None,
                side=ModelTradeSide.BUY,
                quantity=5,
                price=Decimal("10"),
            )
        ]


class FakePriceRepo:
    def get_portfolio_value_series(self, stock_ids, start_date, end_date):
        return {date(2026, 5, 25): {10: Decimal("12")}}


class FakeStockRepo:
    def get_stocks_by_ids(self, stock_ids):
        return [Stock(id=10, ticker="FROTO.IS", name="FROTO")]


def test_model_portfolio_history_simulation_builds_dashboard_models():
    service = ModelPortfolioHistorySimulationService(
        model_portfolio_repo=FakeModelPortfolioRepo(),
        price_repo=FakePriceRepo(),
        stock_repo=FakeStockRepo(),
    )

    positions, snapshots = service.simulate_history(3, date(2026, 5, 25), date(2026, 5, 25))

    assert len(positions) == 1
    assert positions[0].ticker == "FROTO.IS"
    assert positions[0].quantity == 5
    assert positions[0].position_value == Decimal("60")
    assert len(snapshots) == 1
    assert snapshots[0].status == PortfolioStatus.OPEN


def test_model_portfolio_history_simulation_returns_no_data_snapshot_when_price_missing():
    service = ModelPortfolioHistorySimulationService(
        model_portfolio_repo=FakeModelPortfolioRepo(),
        price_repo=SimpleNamespace(get_portfolio_value_series=lambda **kwargs: {}),
        stock_repo=FakeStockRepo(),
    )

    positions, snapshots = service.simulate_history(3, date(2026, 5, 26), date(2026, 5, 26))

    assert positions == []
    assert snapshots[0].status == PortfolioStatus.NO_DATA
