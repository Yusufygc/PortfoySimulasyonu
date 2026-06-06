# src/application/services/portfolio_update_coordinator.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.application.services.portfolio.price_update_service import PriceUpdateService
from src.application.services.analysis.return_calc_service import ReturnCalcService
from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely


@dataclass
class PortfolioUpdateCoordinator:
    """
    UI ile servisler arasındaki 'orkestrasyon' katmanı.

    - Portföyde hangi stock_id'ler var?
    - Bu id'lerin ticker'ları ne?
    - Son tamamlanmış işlem günü kapanış fiyatlarını çek ve DB'ye yaz
    - Son durumda portföyün toplam değeri ve getirisi ne?

    gibi işleri tek noktadan yönetir.
    """

    portfolio_repo: IPortfolioRepository
    stock_repo: IStockRepository
    price_update_service: PriceUpdateService
    return_calc_service: ReturnCalcService
    event_bus: object = None

    def update_today_prices_and_get_snapshot(self):
        """
        Son tamamlanmış işlem gününün kapanış fiyatlarını günceller ve
        aynı tarih için portföy snapshot'ını döner.

        Dönüş:
          (price_update_result, portfolio_snapshot)
        """
        price_date = self.price_update_service.last_completed_trading_day(date.today())

        # 1) Net açık pozisyonu olan hisseleri bul
        portfolio = build_portfolio_safely(self.portfolio_repo.get_all_trades()).portfolio
        stock_ids = sorted(portfolio.active_positions)

        # 2) Bu id'lerin ticker map'ini al
        stock_ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        # 3) Son kapanmış işlem günü fiyatlarını güncelle (yfinance -> DB)
        price_update_result = self.price_update_service.update_closing_prices_for_stocks(
            price_date=price_date,
            stock_ticker_map=stock_ticker_map,
        )

        # Yayın yap
        if self.event_bus and hasattr(price_update_result, "prices"):
            self.event_bus.prices_updated.emit(price_update_result.prices)

        # 4) Aynı kapanış tarihi için portföy değerini hesapla
        portfolio_snapshot = self.return_calc_service.compute_portfolio_value_on(price_date)

        return price_update_result, portfolio_snapshot
