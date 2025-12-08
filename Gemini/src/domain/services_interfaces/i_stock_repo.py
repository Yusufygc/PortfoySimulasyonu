# src/domain/services_interfaces/i_stock_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional, Sequence

from src.domain.models.stock import Stock


class IStockRepository(ABC):
    """
    'stocks' tablosuna erişim için soyut arayüz.

    Amaç:
      - Uygulama & servis katmanı bu interface'e göre programlar.
      - MySQL/başka DB implementasyonları bu interface'i uygular.
    """

    # ---------- READ operasyonları ---------- #

    @abstractmethod
    def get_all_stocks(self) -> List[Stock]:
        """
        Tüm stock kayıtlarını döner.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stock_by_id(self, stock_id: int) -> Optional[Stock]:
        """
        Tek bir stock'u id üzerinden döner.
        Bulunamazsa None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        """
        Tek bir stock'u ticker sembolü üzerinden döner.
        Bulunamazsa None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_stocks_by_ids(self, stock_ids: Sequence[int]) -> List[Stock]:
        """
        Verilen id listesi için Stock listesi döner.
        """
        raise NotImplementedError

    @abstractmethod
    def get_ticker_map_for_stock_ids(
        self,
        stock_ids: Sequence[int],
    ) -> Dict[int, str]:
        """
        Verilen stock_id listesi için:
          { stock_id: ticker }

        map'i döner.

        Gün sonu fiyat güncellemesi (PriceUpdateService) için
        tam ihtiyacımız olan şey.
        """
        raise NotImplementedError

    # ---------- WRITE operasyonları ---------- #

    @abstractmethod
    def insert_stock(self, stock: Stock) -> Stock:
        """
        Yeni bir stock kaydı ekler.
        Dönüş:
          DB'nin atadığı id ile birlikte Stock objesi.
        """
        raise NotImplementedError

    @abstractmethod
    def insert_stocks_bulk(self, stocks: Iterable[Stock]) -> None:
        """
        Birden fazla stock'u toplu insert etmek için opsiyonel metot.
        """
        raise NotImplementedError

    @abstractmethod
    def update_stock(self, stock: Stock) -> None:
        """
        Var olan bir stock kaydını günceller.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_stock(self, stock_id: int) -> None:
        """
        Stock kaydını siler.
        (Gerçekte soft delete tercih edilebilir ama şimdilik basit.)
        """
        raise NotImplementedError
    
    @abstractmethod
    def delete_all_stocks(self) -> None:
        """
        Tüm stock kayıtlarını siler.
        DİKKAT: trades ve daily_prices tabloları önce temizlenmelidir
        (FK kısıtları nedeniyle).
        """
        raise NotImplementedError

