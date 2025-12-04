# src/application/services/price_update_service.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict

from src.domain.models.daily_price import DailyPrice
from src.domain.services_interfaces.i_price_repo import IPriceRepository
from src.domain.services_interfaces.i_market_data_client import IMarketDataClient


@dataclass
class PriceUpdateResult:
    """
    Gün sonu fiyat güncellemesi sonrası basit özet.

    - updated_count: Kaç hisse için fiyat başarıyla güncellendi
    - prices: { stock_id: close_price }
    """
    updated_count: int
    prices: Dict[int, Decimal]


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
    ) -> None:
        self._price_repo = price_repo
        self._market_data_client = market_data_client

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
        if not stock_ticker_map:
            return PriceUpdateResult(updated_count=0, prices={})

        stock_ids = list(stock_ticker_map.keys())
        tickers = [stock_ticker_map[sid] for sid in stock_ids]

        # 1) Market data'dan fiyatları çek
        prices_map = self._market_data_client.get_closing_prices(
            stock_ids=stock_ids,
            tickers=tickers,
            price_date=price_date,
        )
        # prices_map: { stock_id: Decimal(close_price) }

        if not prices_map:
            return PriceUpdateResult(updated_count=0, prices={})

        # 2) DailyPrice domain objelerine çevir
        daily_price_list = [
            DailyPrice(
                id=None,
                stock_id=stock_id,
                price_date=price_date,
                close_price=close_price,
                # currency_code ve source default parametreleri kullanılıyor
            )
            for stock_id, close_price in prices_map.items()
        ]

        # 3) DB'de UPSERT
        self._price_repo.upsert_daily_prices_bulk(daily_price_list)

        # 4) Basit özet dön
        return PriceUpdateResult(
            updated_count=len(prices_map),
            prices=prices_map,
        )
