import pytest
from unittest.mock import MagicMock
from datetime import date
from decimal import Decimal

from src.application.services.portfolio.portfolio_service import PortfolioService
from src.domain.models.trade import Trade

@pytest.fixture
def mock_portfolio_repo():
    return MagicMock()

@pytest.fixture
def mock_price_repo():
    return MagicMock()

@pytest.fixture
def portfolio_service(mock_portfolio_repo, mock_price_repo):
    return PortfolioService(mock_portfolio_repo, mock_price_repo)

def test_calculate_capital_with_profit(portfolio_service, mock_portfolio_repo):
    # Senaryo: 10 lot hisseyi 10 TL'den alıp 15 TL'den satmak
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=10, price=Decimal("15.0")),
    ]
    mock_portfolio_repo.get_all_trades.return_value = trades
    
    capital = portfolio_service.calculate_capital()
    
    # 150 TL satış - 100 TL alış = 50 TL net sermaye girdisi
    assert capital == Decimal("50.0")

def test_calculate_capital_negative_balance_returns_zero(portfolio_service, mock_portfolio_repo):
    # Senaryo: Henüz sadece alış yapılmış (Nakit sermaye hesabı eksiye düşmeyeceği için sıfır dönmeli)
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0")),
    ]
    mock_portfolio_repo.get_all_trades.return_value = trades
    
    capital = portfolio_service.calculate_capital()
    
    # -100 TL nakit hesapta max(0, capital) -> 0 dönmeli
    assert capital == Decimal("0.0")
