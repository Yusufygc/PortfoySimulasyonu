# src/domain/services_interfaces/i_market_data_client.py

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, Sequence

class IMarketDataClient(ABC):
    """
    Piyasa verisi (market data) sağlayıcılarını soyutlayan arayüz.

    Yatırım uygulamamız şu an yfinance kullanacak,
    fakat bu interface sayesinde:
        - yfinance → MySQLPriceRepository                 (gerçek senaryo)
        - FakeMarketClient → Unit test                   (test senaryosu)
        - AlphaVantageMarketClient → İleride genişleme

    şeklinde tamamen plug-and-play yapı kuruyoruz.
    """

    # ---- Temel Fiyat Çekme Operasyonları ---- #

    @abstractmethod
    def get_closing_price(self, stock_id: int, ticker: str, price_date: date) -> Decimal:
        """
        Tek bir hisse için belirli bir tarihteki kapanış fiyatını döner.

        Parametreler:
            stock_id : Domain modelindeki benzersiz kimlik (DB id)
            ticker   : Piyasa sembolü, örn: 'AKBNK.IS'
            price_date : İstenen gün sonu kapanış tarihi

        Dönüş:
            Decimal(close_price)

        Not:
            Eğer veri yoksa implementasyon
            - Exception fırlatabilir
            - veya NaN/None yerine bir özel hata oluşturabilir.
        """
        raise NotImplementedError

    @abstractmethod
    def get_closing_prices(
        self,
        stock_ids: Sequence[int],
        tickers: Sequence[str],
        price_date: date
    ) -> Dict[int, Decimal]:
        """
        Birden fazla hisse için toplu kapanış fiyatı döner.

        Parametreler:
            stock_ids : [1, 3, 7, ...]
            tickers   : ['AKBNK.IS', 'ASELS.IS', ...] — aynı sırada matching olacak
            price_date : kapanış tarihi

        Dönüş:
            {
              stock_id: close_price (Decimal),
              ...
            }

        Not:
            UI’da “Gün Sonu Fiyatlarını Güncelle” butonu tıklandığında
            PriceUpdateService bu fonksiyonu kullanacak.
        """
        raise NotImplementedError

    # ---- Kısa Seri / Multi-Day Fiyat Çekme ---- #

    @abstractmethod
    def get_price_series(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        """
        Bir hissenin belirli bir tarih aralığındaki kapanış fiyat serisini döner.

        Dönüş formatı:
            {
                date1: price1,
                date2: price2,
                ...
            }

        Haftalık / aylık getiri hesapları için faydalı.
        """
        raise NotImplementedError
