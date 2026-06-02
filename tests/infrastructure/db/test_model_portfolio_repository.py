from decimal import Decimal

from src.domain.models.model_portfolio import ModelPortfolio
from src.infrastructure.db.sqlalchemy.repositories.sa_model_portfolio_repository import (
    SQLAlchemyModelPortfolioRepository,
)


def test_model_portfolio_repository_maps_domain_to_orm():
    repo = SQLAlchemyModelPortfolioRepository.__new__(SQLAlchemyModelPortfolioRepository)
    portfolio = ModelPortfolio(
        id=3,
        name="Model",
        description="Test",
        initial_cash=Decimal("250000.00"),
        sort_order=2,
    )

    orm = repo._to_orm_portfolio(portfolio)

    assert orm.id == 3
    assert orm.name == "Model"
    assert orm.description == "Test"
    assert orm.initial_cash == Decimal("250000.00")
    assert orm.sort_order == 2
