# src/domain/repositories/portfolio_repository.py

from __future__ import annotations

from datetime import date
from typing import List, Protocol, runtime_checkable, Optional

from src.domain.models.trade import Trade


@runtime_checkable
class IPortfolioRepository(Protocol):
    """
    İşlem (trade) verisini yöneten repository arayüzü.

    Not: Concrete implementasyonlar (MySQLPortfolioRepository vb.)
    bu interface'e yapısal olarak uyduğu sürece duck-typing ile sorunsuz çalışır.
    """

    # Tüm işlemleri getir (genelde tarih sıralı)
    def get_all_trades(self) -> List[Trade]:
        ...

    # Tek bir işlem ekle
    def insert_trade(self, trade: Trade) -> Trade:
        ...

    # İsteğe bağlı: belirli bir hissenin işlemleri
    def get_trades_by_stock(self, stock_id: int) -> List[Trade]:
        ...

    # Portföyü sıfırlamak için: tüm işlemleri sil
    def delete_all_trades(self) -> None:
        ...
