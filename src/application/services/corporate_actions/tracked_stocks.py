"""Kurumsal aksiyon taramasının hedef hisseleri: ana portföy, izleme listeleri ve model portföylerdeki hisseler."""
from __future__ import annotations

from typing import Optional, Set

from src.domain.ports.repositories.i_model_portfolio_repo import IModelPortfolioRepository
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_watchlist_repo import IWatchlistRepository


def portfolio_stock_ids(portfolio_repo: Optional[IPortfolioRepository]) -> Set[int]:
    if portfolio_repo is None:
        return set()
    return {int(sid) for sid in portfolio_repo.get_all_stock_ids_in_portfolio()}


def watchlist_stock_ids(watchlist_repo: Optional[IWatchlistRepository]) -> Set[int]:
    if watchlist_repo is None:
        return set()
    ids: Set[int] = set()
    for watchlist in watchlist_repo.get_all_watchlists():
        if watchlist.id is not None:
            ids.update(item.stock_id for item in watchlist_repo.get_items_by_watchlist_id(watchlist.id))
    return ids


def model_portfolio_stock_ids(model_repo: Optional[IModelPortfolioRepository]) -> Set[int]:
    if model_repo is None:
        return set()
    ids: Set[int] = set()
    for portfolio in model_repo.get_all_model_portfolios():
        if portfolio.id is not None:
            ids.update(trade.stock_id for trade in model_repo.get_trades_by_portfolio_id(portfolio.id))
    return ids


def tracked_stock_ids(
    portfolio_repo: Optional[IPortfolioRepository],
    watchlist_repo: Optional[IWatchlistRepository],
    model_repo: Optional[IModelPortfolioRepository],
) -> Set[int]:
    return portfolio_stock_ids(portfolio_repo) | watchlist_stock_ids(watchlist_repo) | model_portfolio_stock_ids(model_repo)
