from __future__ import annotations

from decimal import Decimal
from typing import Optional

from src.domain.models.model_portfolio import ModelPortfolio


class ModelPortfolioAdminService:
    def __init__(self, portfolio_repo) -> None:
        self._portfolio_repo = portfolio_repo

    def get_all_portfolios(self):
        return self._portfolio_repo.get_all_model_portfolios()

    def get_portfolio_by_id(self, portfolio_id: int) -> Optional[ModelPortfolio]:
        return self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)

    def create_portfolio(
        self,
        name: str,
        description: Optional[str] = None,
        initial_cash: Decimal = Decimal("100000.00"),
    ) -> ModelPortfolio:
        if not name or not name.strip():
            raise ValueError("Portfoy adi bos olamaz")
        if initial_cash <= 0:
            raise ValueError("Baslangic sermayesi pozitif olmalidir")
        portfolio = ModelPortfolio(
            id=None,
            name=name.strip(),
            description=description.strip() if description else None,
            initial_cash=initial_cash,
        )
        return self._portfolio_repo.create_model_portfolio(portfolio)

    def update_portfolio(
        self,
        portfolio_id: int,
        name: str,
        description: Optional[str] = None,
        initial_cash: Optional[Decimal] = None,
    ) -> None:
        if not name or not name.strip():
            raise ValueError("Portfoy adi bos olamaz")

        existing = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if existing is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")

        updated_portfolio = ModelPortfolio(
            id=portfolio_id,
            name=name.strip(),
            description=description.strip() if description else None,
            initial_cash=initial_cash if initial_cash is not None else existing.initial_cash,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )
        self._portfolio_repo.update_model_portfolio(updated_portfolio)

    def delete_portfolio(self, portfolio_id: int) -> None:
        self._portfolio_repo.delete_model_portfolio(portfolio_id)

