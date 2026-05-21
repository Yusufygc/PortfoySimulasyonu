from unittest.mock import MagicMock
from dataclasses import replace
from datetime import date, time
from decimal import Decimal

import pytest

from src.application.services.reporting.daily_history_models import PortfolioStatus
from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.domain.models.trade import Trade


class DummyStock:
    def __init__(self, stock_id: int, ticker: str):
        self.id = stock_id
        self.ticker = ticker


@pytest.fixture
def mock_portfolio_repo():
    return MagicMock()

@pytest.fixture
def mock_price_repo():
    return MagicMock()

@pytest.fixture
def mock_stock_repo():
    mock = MagicMock()
    mock.get_all_stocks.return_value = []
    return mock

@pytest.fixture
def simulation_service(mock_portfolio_repo, mock_price_repo, mock_stock_repo):
    return HistorySimulationService(
        portfolio_repo=mock_portfolio_repo,
        price_repo=mock_price_repo,
        stock_repo=mock_stock_repo,
    )

def test_simulate_history_no_trades(simulation_service, mock_portfolio_repo):
    mock_portfolio_repo.get_all_trades.return_value = []

    positions, snapshots = simulation_service.simulate_history(date(2026, 1, 1), date(2026, 1, 10))

    assert len(positions) == 0
    assert len(snapshots) == 0

def test_simulate_history_with_trades(simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo):
    class DummyStock:
        id = 1
        ticker = "AAPL"

    mock_stock_repo.get_all_stocks.return_value = [DummyStock()]

    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0")),
    ]
    mock_portfolio_repo.get_all_trades.return_value = trades

    # get_portfolio_value_series döndürmesi: {date: {stock_id: price}}
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 1): {1: Decimal("10.0")},
        date(2026, 1, 2): {1: Decimal("12.0")},
    }

    positions, snapshots = simulation_service.simulate_history(date(2026, 1, 1), date(2026, 1, 2))

    assert len(positions) == 2
    assert len(snapshots) == 2

    last_snapshot = snapshots[1]
    assert last_snapshot.total_value == Decimal("120.0")
    assert last_snapshot.daily_pnl == Decimal("20.0")
    assert last_snapshot.total_cost_basis == Decimal("100.0")

    last_position = positions[1]
    assert last_position.ticker == "AAPL"
    assert last_position.unrealized_pnl_tl == Decimal("20.0")
    assert last_position.weight_pct == Decimal("1.0")


def test_simulate_history_swaps_reversed_date_range(
    simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo
):
    mock_stock_repo.get_all_stocks.return_value = [DummyStock(1, "AAA")]
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=1, price=Decimal("10")),
    ]
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 1): {1: Decimal("10")},
        date(2026, 1, 2): {1: Decimal("11")},
    }

    _, snapshots = simulation_service.simulate_history(date(2026, 1, 2), date(2026, 1, 1))

    assert [snapshot.date for snapshot in snapshots] == [date(2026, 1, 1), date(2026, 1, 2)]
    mock_price_repo.get_portfolio_value_series.assert_called_once_with(
        stock_ids=[1],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
    )


def test_simulate_history_marks_weekend_and_no_data_statuses(
    simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo
):
    mock_stock_repo.get_all_stocks.return_value = [DummyStock(1, "AAA")]
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 2), quantity=1, price=Decimal("10")),
    ]
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 2): {1: Decimal("10")},
    }

    _, snapshots = simulation_service.simulate_history(date(2026, 1, 2), date(2026, 1, 5))

    assert snapshots[0].status == PortfolioStatus.OPEN
    assert snapshots[1].status == PortfolioStatus.WEEKEND
    assert snapshots[2].status == PortfolioStatus.WEEKEND
    assert snapshots[3].status == PortfolioStatus.NO_DATA


def test_simulate_history_applies_same_day_trades_by_time(
    simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo
):
    mock_stock_repo.get_all_stocks.return_value = [DummyStock(1, "AAA")]
    buy = Trade.create_buy(
        stock_id=1,
        trade_date=date(2026, 1, 5),
        trade_time=time(9, 30),
        quantity=10,
        price=Decimal("10"),
    )
    sell = Trade.create_sell(
        stock_id=1,
        trade_date=date(2026, 1, 5),
        trade_time=time(10, 30),
        quantity=4,
        price=Decimal("11"),
    )
    mock_portfolio_repo.get_all_trades.return_value = [sell, buy]
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 5): {1: Decimal("12")},
    }

    positions, snapshots = simulation_service.simulate_history(date(2026, 1, 5), date(2026, 1, 5))

    assert positions[0].quantity == 6
    assert positions[0].cost_basis == Decimal("60")
    assert snapshots[0].total_value == Decimal("72")


def test_simulate_history_applies_same_day_trades_by_id_when_time_is_equal(
    simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo
):
    mock_stock_repo.get_all_stocks.return_value = [DummyStock(1, "AAA")]
    trade_time = time(9, 30)
    buy = replace(
        Trade.create_buy(1, date(2026, 1, 5), 10, Decimal("10"), trade_time=trade_time),
        id=1,
    )
    sell = replace(
        Trade.create_sell(1, date(2026, 1, 5), 4, Decimal("11"), trade_time=trade_time),
        id=2,
    )
    mock_portfolio_repo.get_all_trades.return_value = [sell, buy]
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 5): {1: Decimal("12")},
    }

    positions, _ = simulation_service.simulate_history(date(2026, 1, 5), date(2026, 1, 5))

    assert positions[0].quantity == 6


def test_simulate_history_skips_closed_positions_and_handles_zero_price(
    simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo
):
    mock_stock_repo.get_all_stocks.return_value = [DummyStock(1, "AAA"), DummyStock(2, "BBB")]
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(1, date(2026, 1, 5), 5, Decimal("10")),
        Trade.create_sell(1, date(2026, 1, 5), 5, Decimal("10")),
        Trade.create_buy(2, date(2026, 1, 5), 3, Decimal("7")),
    ]
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 5): {1: Decimal("12"), 2: Decimal("0")},
    }

    positions, snapshots = simulation_service.simulate_history(date(2026, 1, 5), date(2026, 1, 5))

    assert [position.ticker for position in positions] == ["BBB"]
    assert positions[0].position_value == Decimal("0")
    assert snapshots[0].total_value is None


def test_simulate_history_carries_last_value_on_no_price_day(
    simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo
):
    mock_stock_repo.get_all_stocks.return_value = [DummyStock(1, "AAA")]
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(1, date(2026, 1, 5), 2, Decimal("10")),
    ]
    mock_price_repo.get_portfolio_value_series.return_value = {
        date(2026, 1, 5): {1: Decimal("11")},
    }

    _, snapshots = simulation_service.simulate_history(date(2026, 1, 5), date(2026, 1, 6))

    assert snapshots[0].total_value == Decimal("22")
    assert snapshots[1].status == PortfolioStatus.NO_DATA
    assert snapshots[1].total_value == Decimal("22")
    assert snapshots[1].daily_pnl == Decimal("0")
