# src/application/services/price_update_service.py (özet iskelet)

from datetime import date
from typing import Sequence

from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from src.domain.services_interfaces.i_price_repo import IPriceRepository
from src.domain.models.daily_price import DailyPrice


class PriceUpdateService:
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        market_data_client,  # yfinance client interface'i de ayrıca tanımlayacağız
    ):
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo
        self._market_data_client = market_data_client

    def update_all_closing_prices(self, price_date: date) -> None:
        # Portföydeki tüm hisseler:
        stock_ids: Sequence[int] = self._portfolio_repo.get_all_stock_ids_in_portfolio()

        # yfinance üzerinden fiyatları çek:
        prices_map = self._market_data_client.get_closing_prices(
            stock_ids=stock_ids,
            price_date=price_date,
        )
        # prices_map: { stock_id: Decimal(close_price) }

        daily_price_list = [
            DailyPrice(
                id=None,
                stock_id=stock_id,
                price_date=price_date,
                close_price=close_price,
            )
            for stock_id, close_price in prices_map.items()
        ]

        # DB'ye yaz:
        self._price_repo.upsert_daily_prices_bulk(daily_price_list)
