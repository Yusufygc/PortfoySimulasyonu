"""Model portföy: bölünme küsurat nakdi (FRACTION) nakde eklenir, yatırılan sermayeyi artırmaz."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.planning.model_portfolio_trade_service import ModelPortfolioTradeSimulator
from src.domain.models.model_portfolio import ModelPortfolioCashMovement, ModelPortfolioCashMovementType


def test_fraction_cash_adds_cash_without_changing_invested_capital():
    portfolio = SimpleNamespace(initial_cash=Decimal("1000"))
    fraction = ModelPortfolioCashMovement(
        id=1, portfolio_id=9, movement_date=date(2026, 8, 21), movement_time=None,
        type=ModelPortfolioCashMovementType.FRACTION, amount=Decimal("0.50"),
    )
    result = ModelPortfolioTradeSimulator().simulate(portfolio, [], [fraction])
    assert result.cash == Decimal("1000.50")
    assert result.invested_capital == Decimal("1000")
    assert result.violations == []
