from datetime import date, time
from decimal import Decimal

from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioCashMovement
from src.infrastructure.db.sqlalchemy.repositories.sa_model_portfolio_repository import (
    _to_domain_cash_movement,
    _to_orm_cash_movement,
    _to_orm_portfolio,
)


def test_model_portfolio_repository_maps_domain_to_orm():
    portfolio = ModelPortfolio(
        id=3,
        name="Model",
        description="Test",
        initial_cash=Decimal("250000.00"),
        sort_order=2,
    )

    orm = _to_orm_portfolio(portfolio)

    assert orm.id == 3
    assert orm.name == "Model"
    assert orm.description == "Test"
    assert orm.initial_cash == Decimal("250000.00")
    assert orm.sort_order == 2


def test_model_portfolio_repository_maps_cash_movement_domain_to_orm():
    movement = ModelPortfolioCashMovement.create_deposit(
        portfolio_id=3,
        amount=Decimal("5000.00"),
        movement_date=date(2026, 1, 3),
        movement_time=time(10, 15),
        notes="ek sermaye",
    )

    orm = _to_orm_cash_movement(movement)
    domain = _to_domain_cash_movement(orm)

    assert orm.portfolio_id == 3
    assert orm.type == "DEPOSIT"
    assert orm.amount == Decimal("5000.00")
    assert domain.portfolio_id == 3
    assert domain.amount == Decimal("5000.00")
    assert domain.notes == "ek sermaye"
