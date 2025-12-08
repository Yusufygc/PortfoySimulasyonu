# src/domain/repositories/stock_repository.py

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

from src.domain.models.stock import Stock


@runtime_checkable
class IStockRepository(Protocol):
    """
    Hisse (stock) meta bilgisini yöneten repository arayüzü.
    Genellikle stocks tablosuna karşılık gelir.
    """

    def get_or_create_stock(
        self,
        ticker: str,
        name: Optional[str] = None,
        currency_code: str = "TRY",
    ) -> Stock:
        """
        Ticker'a göre hisseyi getir; yoksa oluşturup döner.
        """
        ...

    def get_stock_by_id(self, stock_id: int) -> Optional[Stock]:
        ...

    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        ...

    def get_all_stocks(self) -> List[Stock]:
        ...

    def delete_all_stocks(self) -> None:
        """
        Tüm hisse kayıtlarını siler (portföy reset senaryosu için).
        """
        ...

    def get_ticker_map(self) -> Dict[int, str]:
        """
        Hızlı erişim için: stock_id -> ticker map'i.
        (Uygulamada basitçe get_all_stocks ile üretilebilir.)
        """
        ...
