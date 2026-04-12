import pytest
from unittest.mock import MagicMock
from datetime import date
from decimal import Decimal

from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.domain.models.trade import Trade

@pytest.fixture
def mock_portfolio_repo():
    return MagicMock()

@pytest.fixture
def mock_price_repo():
    return MagicMock()

@pytest.fixture
def mock_stock_repo():
    mock = MagicMock()
    # Stub get_all_stocks to return an empty list initially
    mock.get_all_stocks.return_value = []
    return mock

@pytest.fixture
def mock_market_client():
    return MagicMock()

@pytest.fixture
def simulation_service(mock_portfolio_repo, mock_price_repo, mock_stock_repo, mock_market_client):
    return HistorySimulationService(
        portfolio_repo=mock_portfolio_repo,
        price_repo=mock_price_repo,
        stock_repo=mock_stock_repo,
        market_data_client=mock_market_client
    )

def test_simulate_history_no_trades(simulation_service, mock_portfolio_repo):
    # Senaryo: Hiç trade yoksa
    mock_portfolio_repo.get_all_trades.return_value = []
    
    positions, snapshots = simulation_service.simulate_history(date(2026, 1, 1), date(2026, 1, 10))
    
    assert len(positions) == 0
    assert len(snapshots) == 0

def test_simulate_history_with_trades(simulation_service, mock_portfolio_repo, mock_stock_repo, mock_price_repo):
    # Senaryo: Alış yapılmış, ertesi gün fiyat artmış
    class DummyStock:
        id = 1
        ticker = "AAPL"
        
    mock_stock_repo.get_all_stocks.return_value = [DummyStock()]
    
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0")),
    ]
    mock_portfolio_repo.get_all_trades.return_value = trades
    
    # Fiyat tanımlaması: 1. Gün -> 10, 2. Gün -> 12
    def get_prices_for_date(d):
        if d == date(2026, 1, 1):
            return {1: Decimal("10.0")}
        elif d == date(2026, 1, 2):
            return {1: Decimal("12.0")}
        return {}
        
    mock_price_repo.get_prices_for_date.side_effect = get_prices_for_date
    
    positions, snapshots = simulation_service.simulate_history(date(2026, 1, 1), date(2026, 1, 2))
    
    # Beklenti: 2 gün (1 Ocak ve 2 Ocak), 1 hisse pozisyonu
    assert len(positions) == 2
    assert len(snapshots) == 2
    
    # 2. gün snapshot assert
    last_snapshot = snapshots[1]
    assert last_snapshot.total_value == Decimal("120.0")  # (10 lot * 12.0 TL)
    assert last_snapshot.daily_pnl == Decimal("20.0")     # 120 - 100
    assert last_snapshot.total_cost_basis == Decimal("100.0")
    
    # 2. gün position assert
    last_position = positions[1]
    assert last_position.ticker == "AAPL"
    assert last_position.unrealized_pnl_tl == Decimal("20.0")
    assert last_position.weight_pct == Decimal("1.0")

