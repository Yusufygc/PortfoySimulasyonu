from __future__ import annotations

from decimal import Decimal
from typing import Optional

from .model_portfolio_admin_service import ModelPortfolioAdminService
from .model_portfolio_snapshot_service import ModelPortfolioSnapshotService
from .model_portfolio_trade_service import ModelPortfolioTradeService


class ModelPortfolioService:
    """
    Public facade that preserves the old API while delegating to narrower services.
    """

    def __init__(
        self,
        model_portfolio_repo,
        stock_repo,
    ) -> None:
        self._admin = ModelPortfolioAdminService(model_portfolio_repo)
        self._trade = ModelPortfolioTradeService(model_portfolio_repo, stock_repo)
        self._snapshot = ModelPortfolioSnapshotService(model_portfolio_repo, stock_repo, self._trade)

    def get_all_portfolios(self):
        return self._admin.get_all_portfolios()

    def get_portfolio_by_id(self, portfolio_id: int):
        return self._admin.get_portfolio_by_id(portfolio_id)

    def create_portfolio(
        self,
        name: str,
        description: Optional[str] = None,
        initial_cash: Decimal = Decimal("100000.00"),
    ):
        return self._admin.create_portfolio(name=name, description=description, initial_cash=initial_cash)

    def update_portfolio(
        self,
        portfolio_id: int,
        name: str,
        description: Optional[str] = None,
        initial_cash: Optional[Decimal] = None,
    ) -> None:
        self._admin.update_portfolio(
            portfolio_id=portfolio_id,
            name=name,
            description=description,
            initial_cash=initial_cash,
        )

    def delete_portfolio(self, portfolio_id: int) -> None:
        self._admin.delete_portfolio(portfolio_id)

    def get_portfolio_trades(self, portfolio_id: int):
        return self._trade.get_portfolio_trades(portfolio_id)

    def add_trade(self, *args, **kwargs):
        return self._trade.add_trade(*args, **kwargs)

    def add_trade_by_ticker(self, *args, **kwargs):
        return self._trade.add_trade_by_ticker(*args, **kwargs)

    def delete_trade(self, trade_id: int) -> None:
        self._trade.delete_trade(trade_id)

    def get_positions(self, portfolio_id: int):
        return self._trade.get_positions(portfolio_id)

    def get_remaining_cash(self, portfolio_id: int):
        return self._trade.get_remaining_cash(portfolio_id)

    def get_portfolio_summary(self, *args, **kwargs):
        return self._snapshot.get_portfolio_summary(*args, **kwargs)

    def get_positions_with_details(self, *args, **kwargs):
        return self._snapshot.get_positions_with_details(*args, **kwargs)

    def get_trade_count(self, portfolio_id: int):
        return self._snapshot.get_trade_count(portfolio_id)
