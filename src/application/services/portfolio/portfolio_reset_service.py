from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.ports.repositories.i_model_portfolio_repo import IModelPortfolioRepository
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.repositories.i_watchlist_repo import IWatchlistRepository


@dataclass
class PortfolioResetService:
    """
    Tum portfoyu sifirlamak icin kullanilan servis.

    Silme sirasi FK bagimliliklarina gore child tablolardan parent tabloya dogrudur:
    model_portfolio_trades/watchlist_items -> trades -> daily_prices -> stocks.
    Watchlist ve model portfoy repolari opsiyoneldir; eski test/fake kullanimlari
    yalnizca ana portfoy resetini calistirabilir.
    """

    portfolio_repo: IPortfolioRepository
    price_repo: IPriceRepository
    stock_repo: IStockRepository
    watchlist_repo: Optional[IWatchlistRepository] = None
    model_portfolio_repo: Optional[IModelPortfolioRepository] = None

    def reset_all(self) -> None:
        if self.model_portfolio_repo is not None:
            self.model_portfolio_repo.delete_all_model_portfolios()
        if self.watchlist_repo is not None:
            self.watchlist_repo.delete_all_watchlists()

        self.portfolio_repo.delete_all_trades()
        self.price_repo.delete_all_prices()
        self.stock_repo.delete_all_stocks()
