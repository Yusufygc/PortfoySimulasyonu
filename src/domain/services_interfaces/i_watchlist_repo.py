# src/domain/services_interfaces/i_watchlist_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.watchlist import Watchlist, WatchlistItem


class IWatchlistRepository(ABC):
    """
    'watchlists' ve 'watchlist_items' tablolarına erişim için soyut arayüz.
    """

    # ---------- Watchlist READ operasyonları ---------- #

    @abstractmethod
    def get_all_watchlists(self) -> List[Watchlist]:
        """Tüm watchlist kayıtlarını döner."""
        raise NotImplementedError

    @abstractmethod
    def get_watchlist_by_id(self, watchlist_id: int) -> Optional[Watchlist]:
        """Tek bir watchlist'i id üzerinden döner. Bulunamazsa None."""
        raise NotImplementedError

    # ---------- Watchlist WRITE operasyonları ---------- #

    @abstractmethod
    def create_watchlist(self, watchlist: Watchlist) -> Watchlist:
        """
        Yeni bir watchlist oluşturur.
        Dönüş: DB'nin atadığı id ile birlikte Watchlist objesi.
        """
        raise NotImplementedError

    @abstractmethod
    def update_watchlist(self, watchlist: Watchlist) -> None:
        """Var olan bir watchlist kaydını günceller."""
        raise NotImplementedError

    @abstractmethod
    def delete_watchlist(self, watchlist_id: int) -> None:
        """
        Watchlist'i siler.
        Not: CASCADE ayarı nedeniyle içindeki item'lar da silinir.
        """
        raise NotImplementedError

    # ---------- WatchlistItem READ operasyonları ---------- #

    @abstractmethod
    def get_items_by_watchlist_id(self, watchlist_id: int) -> List[WatchlistItem]:
        """Belirli bir watchlist'e ait tüm item'ları döner."""
        raise NotImplementedError

    @abstractmethod
    def get_item_by_id(self, item_id: int) -> Optional[WatchlistItem]:
        """Tek bir item'ı id üzerinden döner. Bulunamazsa None."""
        raise NotImplementedError

    # ---------- WatchlistItem WRITE operasyonları ---------- #

    @abstractmethod
    def add_item_to_watchlist(self, item: WatchlistItem) -> WatchlistItem:
        """
        Watchlist'e yeni bir hisse ekler.
        Dönüş: DB'nin atadığı id ile birlikte WatchlistItem objesi.
        """
        raise NotImplementedError

    @abstractmethod
    def remove_item_from_watchlist(self, item_id: int) -> None:
        """Watchlist'ten bir hisseyi çıkarır."""
        raise NotImplementedError

    @abstractmethod
    def remove_stock_from_watchlist(self, watchlist_id: int, stock_id: int) -> None:
        """Watchlist'ten belirli bir stock'u çıkarır."""
        raise NotImplementedError

    @abstractmethod
    def is_stock_in_watchlist(self, watchlist_id: int, stock_id: int) -> bool:
        """Bir stock'un watchlist'te olup olmadığını kontrol eder."""
        raise NotImplementedError
