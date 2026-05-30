import pytest
from unittest.mock import MagicMock
from datetime import date
from decimal import Decimal

from src.application.services.portfolio.portfolio_service import PortfolioService
from src.domain.models.cash_movement import CashMovement
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


class FakeCashMovementRepo:
    def __init__(self, movements=None):
        self._movements = movements or []

    def get_all_movements(self):
        return list(self._movements)

    def get_movements_until(self, movement_date, movement_time=None):
        return [movement for movement in self._movements if movement.movement_date <= movement_date]

def test_calculate_capital_with_legacy_profit_does_not_create_debt(portfolio_service, mock_portfolio_repo):
    # Senaryo: 10 lot hisseyi 10 TL'den alıp 15 TL'den satmak
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=10, price=Decimal("15.0")),
    ]
    mock_portfolio_repo.get_all_trades.return_value = trades
    
    capital = portfolio_service.calculate_capital()
    
    # 150 TL satış - 100 TL alış = 50 TL net sermaye girdisi
    assert capital == Decimal("150.0")

def test_calculate_capital_floors_legacy_overdraft_to_zero(portfolio_service, mock_portfolio_repo):
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0")),
    ]
    mock_portfolio_repo.get_all_trades.return_value = trades
    
    capital = portfolio_service.calculate_capital()
    
    assert capital == Decimal("0")


def test_legacy_overdraft_does_not_eat_later_sell_cash(mock_portfolio_repo, mock_price_repo):
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=4, price=Decimal("12")),
    ]
    service = PortfolioService(mock_portfolio_repo, mock_price_repo)

    assert service.get_cash_balance() == Decimal("48")


def test_cash_balance_uses_cash_movements_and_valid_trades(mock_portfolio_repo, mock_price_repo):
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 2), quantity=10, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 3), quantity=4, price=Decimal("12")),
    ]
    cash_repo = FakeCashMovementRepo(
        [
            CashMovement.create_deposit(Decimal("200"), date(2026, 1, 1)),
            CashMovement.create_withdraw(Decimal("25"), date(2026, 1, 4)),
        ]
    )
    service = PortfolioService(mock_portfolio_repo, mock_price_repo, cash_movement_repo=cash_repo)

    assert service.get_cash_balance() == Decimal("123")


def test_invalid_sell_is_reported_and_excluded_from_portfolio(mock_portfolio_repo, mock_price_repo):
    mock_portfolio_repo.get_all_trades.return_value = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=5, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=7, price=Decimal("11")),
    ]
    service = PortfolioService(mock_portfolio_repo, mock_price_repo)

    health = service.get_portfolio_health()

    assert len(health.invalid_trades) == 1
    assert health.invalid_trades[0].available_quantity == 5
    assert health.portfolio.positions[1].total_quantity == 5
