# src/domain/services_interfaces/i_price_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from src.domain.models.daily_price import DailyPrice


class IPriceRepository(ABC):
    """
    Günlük fiyat (daily_prices) verisine erişim için soyut arayüz.

    Gün sonu fiyat güncelleme, haftalık/aylık getiri hesabı gibi
    use-case'ler bu interface üzerinden çalışır.
    """

    # --------- READ operasyonları --------- #

    @abstractmethod
    def get_price_for_date(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        """
        Belirli bir hisse için, belirli bir güne ait kapanış fiyatını döner.
        Bulunamazsa None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_prices_for_date(self, price_date: date) -> Dict[int, Decimal]:
        """
        Verilen tarihte, portföydeki tüm hisseler için kapanış fiyatı map'i döner.

        Dönüş:
          { stock_id: close_price }
        """
        raise NotImplementedError

    @abstractmethod
    def get_last_price_before(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        """
        Verilen tarihten önceki (veya aynı gün) en son kapanış fiyatını döner.
        Veri boş ise None.

        Haftalık/aylık getiri hesabında başlangıç veya bitiş fiyatı yoksa
        en yakın önceki günü bulmak için kullanılabilir.
        """
        raise NotImplementedError

    @abstractmethod
    def get_price_series(
        self,
        stock_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DailyPrice]:
        """
        Belirli bir hisse için, verilen tarih aralığındaki günlük kapanış serisini döner.
        """
        raise NotImplementedError

    @abstractmethod
    def get_portfolio_value_series(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Dict[int, Decimal]]:
        """
        (Opsiyonel ama güçlü bir arayüz.)

        Verilen hisse listesi ve tarih aralığı için:

          {
            price_date: {
                stock_id: close_price,
                ...
            },
            ...
          }

        şeklinde nested map döner.

        Haftalık/aylık portföy getiri hesaplarını kolaylaştırır.
        Concrete implementation günlük fiyatlar üzerinden hesaplayabilir
        veya direkt view kullanabilir.
        """
        raise NotImplementedError

    # --------- WRITE operasyonları --------- #

    @abstractmethod
    def upsert_daily_price(self, daily_price: DailyPrice) -> DailyPrice:
        """
        Tek bir günlük fiyat kaydını ekler veya günceller (UPSERT).

        Dönüş:
          - DB id'si atanmış DailyPrice objesi.
        """
        raise NotImplementedError

    @abstractmethod
    def upsert_daily_prices_bulk(self, prices: Iterable[DailyPrice]) -> None:
        """
        Birden fazla daily price kaydını toplu UPSERT eder.

        Gün sonu fiyat güncellemesi butonuna bastığında:
          - yfinance → DailyPrice listesi
          - IPriceRepository.upsert_daily_prices_bulk(...) ile DB'ye yazılır.
        """
        raise NotImplementedError
