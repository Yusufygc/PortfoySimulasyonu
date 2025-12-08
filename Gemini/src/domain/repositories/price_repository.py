# src/domain/repositories/price_repository.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Optional, Protocol, runtime_checkable, List


@runtime_checkable
class IPriceRepository(Protocol):
    """
    Gün sonu fiyatlarını (daily close) yöneten repository arayüzü.
    Genellikle daily_prices tablosuna karşılık gelir.
    """

    def upsert_daily_price(
        self,
        stock_id: int,
        price_date: date,
        close_price: Decimal,
    ) -> None:
        """
        Belirli bir hisse + tarih için kapanış fiyatını ekler veya günceller.
        """
        ...

    def get_price(
        self,
        stock_id: int,
        price_date: date,
    ) -> Optional[Decimal]:
        """
        Belirli bir hisse + tarihteki kapanış fiyatını döner.
        Kayıt yoksa None.
        """
        ...

    def get_prices_for_date(
        self,
        price_date: date,
    ) -> Dict[int, Decimal]:
        """
        Verilen gün için: stock_id -> close_price map'i döner.
        """
        ...

    def delete_all_prices(self) -> None:
        """
        Tüm fiyat kayıtlarını siler (portföy reset senaryosu için).
        """
        ...
