# src/application/services/price_update_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict

from src.domain.models.daily_price import DailyPrice
from src.application.services.market.trading_calendar import MarketTradingCalendar, WeekdayTradingCalendar
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient


@dataclass
class PriceUpdateResult:
    """
    Gün sonu fiyat güncellemesi sonrası basit özet.

    - updated_count: Kaç hisse için fiyat başarıyla güncellendi
    - prices: { stock_id: close_price }
    """
    updated_count: int
    prices: Dict[int, Decimal]
    skipped_reason: str | None = None


class PriceUpdateService:
    """
    Gün sonu kapanış fiyatlarını güncellemek için kullanılan application service.

    Bu servis:
      - Market data sağlayıcısından (IMarketDataClient) fiyatları çeker,
      - Domain model (DailyPrice) üretir,
      - IPriceRepository üzerinden DB'ye (UPSERT) yazar.

    Hangi hisselerin güncelleneceği bu sınıfa,
    { stock_id: ticker } map'i olarak dışarıdan verilir.
    """

    def __init__(
        self,
        price_repo: IPriceRepository,
        market_data_client: IMarketDataClient,
        trading_calendar: MarketTradingCalendar | None = None,
    ) -> None:
        self._price_repo = price_repo
        self._market_data_client = market_data_client
        self._trading_calendar = trading_calendar or WeekdayTradingCalendar()

    def update_closing_prices_for_stocks(
        self,
        price_date: date,
        stock_ticker_map: Dict[int, str],
    ) -> PriceUpdateResult:
        """
        Verilen tarihte, verilen hisseler için kapanış fiyatlarını günceller.

        Parametreler:
            price_date: Gün sonu tarihi (ör: date.today())
            stock_ticker_map: { stock_id: 'AKBNK.IS', ... }

        Dönüş:
            PriceUpdateResult
        """
        if not self._trading_calendar.is_trading_day(price_date):
            return PriceUpdateResult(
                updated_count=0,
                prices={},
                skipped_reason=f"BIST kapalı ({price_date:%d.%m.%Y}); fiyat güncellemesi atlandı.",
            )

        if not stock_ticker_map:
            return PriceUpdateResult(updated_count=0, prices={})

        prices_map = self._fetch_closing_prices(price_date, stock_ticker_map)

        if not prices_map:
            return PriceUpdateResult(updated_count=0, prices={})

        self._price_repo.upsert_daily_prices_bulk(self._daily_prices(price_date, prices_map))

        return PriceUpdateResult(
            updated_count=len(prices_map),
            prices=prices_map,
        )

    def _fetch_closing_prices(self, price_date: date, stock_ticker_map: Dict[int, str]) -> Dict[int, Decimal]:
        stock_ids = list(stock_ticker_map.keys())
        return self._market_data_client.get_closing_prices(
            stock_ids=stock_ids,
            tickers=[stock_ticker_map[stock_id] for stock_id in stock_ids],
            price_date=price_date,
        )

    @staticmethod
    def _daily_prices(price_date: date, prices_map: Dict[int, Decimal]) -> list[DailyPrice]:
        return [
            DailyPrice(
                id=None,
                stock_id=stock_id,
                price_date=price_date,
                close_price=close_price,
            )
            for stock_id, close_price in prices_map.items()
        ]
