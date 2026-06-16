from __future__ import annotations

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
        market_session_service=None,
    ) -> None:
        self._admin = ModelPortfolioAdminService(model_portfolio_repo)
        self._trade = ModelPortfolioTradeService(model_portfolio_repo, stock_repo, market_session_service)
        self._snapshot = ModelPortfolioSnapshotService(model_portfolio_repo, stock_repo, self._trade)


def _delegated_method(delegate_attr: str, method_name: str):
    def method(self, *args, **kwargs):
        return getattr(getattr(self, delegate_attr), method_name)(*args, **kwargs)

    method.__name__ = method_name
    return method


for _delegate_attr, _method_names in {
    "_admin": (
        "get_all_portfolios",
        "get_portfolio_by_id",
        "create_portfolio",
        "update_portfolio",
        "delete_portfolio",
        "reorder_portfolios",
    ),
    "_trade": (
        "get_portfolio_trades",
        "get_first_trade_date",
        "get_stock_trades",
        "add_trade",
        "add_trade_by_ticker",
        "delete_trade",
        "get_positions",
        "get_remaining_cash",
        "add_capital_movement",
        "get_capital_movements",
        "get_invested_capital",
        "get_position_quantity_as_of",
        "get_valid_trades",
    ),
    "_snapshot": (
        "get_portfolio_summary",
        "get_positions_with_details",
        "get_trade_count",
        "get_active_position_count",
    ),
}.items():
    for _method_name in _method_names:
        setattr(ModelPortfolioService, _method_name, _delegated_method(_delegate_attr, _method_name))

del _delegate_attr, _method_name, _method_names
