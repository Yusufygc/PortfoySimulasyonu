# src/application/services/portfolio_reset_service.py

from __future__ import annotations

from dataclasses import dataclass

from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from src.domain.services_interfaces.i_price_repo import IPriceRepository
from src.domain.services_interfaces.i_stock_repo import IStockRepository


@dataclass
class PortfolioResetService:
    """
    Tüm portföyü sıfırlamak için kullanılan servis.

    Sıra:
      1) trades
      2) daily_prices (+ snapshots)
      3) stocks
    (FK kısıtları yüzünden bu sıralama önemli.)
    """

    portfolio_repo: IPortfolioRepository
    price_repo: IPriceRepository
    stock_repo: IStockRepository

    def reset_all(self) -> None:
        # Önce trades (trades.stock_id → stocks.id)
        self.portfolio_repo.delete_all_trades()
        # Sonra fiyatlar & snapshotlar (daily_prices.stock_id → stocks.id)
        self.price_repo.delete_all_prices()
        # En son hisseler
        self.stock_repo.delete_all_stocks()
