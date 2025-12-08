# src/application/services/portfolio_update_coordinator.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from src.domain.services_interfaces.i_stock_repo import IStockRepository
from src.application.services.price_update_service import PriceUpdateService
from src.application.services.return_calc_service import ReturnCalcService


@dataclass
class PortfolioUpdateCoordinator:
    """
    UI ile servisler arasındaki 'orkestrasyon' katmanı.

    - Portföyde hangi stock_id'ler var?
    - Bu id'lerin ticker'ları ne?
    - Gün sonu fiyatlarını çek ve DB'ye yaz
    - Son durumda portföyün toplam değeri ve getirisi ne?

    gibi işleri tek noktadan yönetir.
    """

    portfolio_repo: IPortfolioRepository
    stock_repo: IStockRepository
    price_update_service: PriceUpdateService
    return_calc_service: ReturnCalcService

    def update_today_prices_and_get_snapshot(self):
        """
        Bugünün kapanış fiyatlarını günceller ve gün sonu portföy snapshot'ını döner.

        Dönüş:
          (price_update_result, portfolio_snapshot)
        """
        today = date.today()

        # 1) Portföyde trade'i olan tüm hisseleri bul
        stock_ids = self.portfolio_repo.get_all_stock_ids_in_portfolio()

        # 2) Bu id'lerin ticker map'ini al
        stock_ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        # 3) Gün sonu fiyatları güncelle (yfinance → DB)
        price_update_result = self.price_update_service.update_closing_prices_for_stocks(
            price_date=today,
            stock_ticker_map=stock_ticker_map,
        )

        # 4) Güncel portföy değerini hesapla
        portfolio_snapshot = self.return_calc_service.compute_portfolio_value_on(today)

        return price_update_result, portfolio_snapshot
