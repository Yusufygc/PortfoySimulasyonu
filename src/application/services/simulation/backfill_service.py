# src/application/services/backfill_service.py

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)

from src.domain.models.daily_price import DailyPrice
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient
from src.application.services.corporate_actions.price_adjustment_service import adjusted_market_price


class BackfillService:
    """
    Geçmişe yönelik fiyat verisi yönetim servisi.

    İki ana işlev:
        1. backfill_range: market data portundan tarih aralığı için veri çeker ve DB'ye kaydeder
        2. delete_range: belirli tarih aralığındaki fiyat verilerini siler
    """

    def __init__(
        self,
        stock_repo,
        price_repo: IPriceRepository,
        market_data_client: IMarketDataClient,
        corporate_action_repo: ICorporateActionRepository | None = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._market_data_client = market_data_client
        self._corporate_action_repo = corporate_action_repo

    def backfill_range(self, start_date: date, end_date: date) -> int:
        """
        Belirtilen tarih aralığı için market data portundan veri çeker ve DB'ye kaydeder.

        Args:
            start_date: Başlangıç tarihi (dahil)
            end_date: Bitiş tarihi (dahil)

        Returns:
            Kaydedilen fiyat verisi sayısı
        """
        if start_date > end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

        # Hisseleri al
        stocks = self._stock_repo.get_all_stocks()
        if not stocks:
            raise ValueError("Veritabanında kayıtlı hisse yok.")

        prices_to_save: list[DailyPrice] = []
        for stock in stocks:
            if stock.id is None:
                logger.warning("Stock %s has no id, skipping backfill", stock.ticker)
                continue
            prices_to_save.extend(
                self._build_daily_prices(
                    stock_id=stock.id,
                    ticker=stock.ticker,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

        # DB'ye kaydet
        if prices_to_save:
            self._price_repo.upsert_daily_prices_bulk(prices_to_save)

        return len(prices_to_save)

    def delete_range(self, start_date: date, end_date: date) -> int:
        """
        Belirtilen tarih aralığındaki fiyat verilerini siler.

        Args:
            start_date: Başlangıç tarihi (dahil)
            end_date: Bitiş tarihi (dahil)

        Returns:
            Silinen kayıt sayısı
        """
        if start_date > end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

        return self._price_repo.delete_prices_in_range(start_date, end_date)

    def backfill_for_single_stock(
        self,
        stock_id: int,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Tek bir hisse için market data portundan fiyat çekip daily_prices'ı günceller.
        Sermaye artırımı sonrası retroaktif fiyat düzeltmesi için kullanılır.
        Eski kayıtlar upsert ile üzerine yazılır.
        """
        if start_date > end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

        prices = self._build_daily_prices(
            stock_id=stock_id,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        if prices:
            self._price_repo.upsert_daily_prices_bulk(prices)

        return len(prices)

    def _build_daily_prices(
        self,
        stock_id: int,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> list[DailyPrice]:
        series = self._market_data_client.get_price_series(ticker, start_date, end_date)
        actions = (
            self._corporate_action_repo.get_by_stock(stock_id)
            if self._corporate_action_repo is not None
            else []
        )
        prices = [
            DailyPrice(
                id=None,
                stock_id=stock_id,
                price_date=price_date,
                close_price=adjusted_market_price(self._to_decimal(close_price), price_date, actions),
            )
            for price_date, close_price in sorted(series.items())
            if start_date <= price_date <= end_date
        ]
        return prices

    @staticmethod
    def _to_decimal(value: Decimal | int | float | str) -> Decimal:
        return value if isinstance(value, Decimal) else Decimal(str(value))
