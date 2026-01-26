# src/application/services/watchlist_service.py

from __future__ import annotations

from typing import List, Optional, Dict, Any
from decimal import Decimal

from src.domain.models.watchlist import Watchlist, WatchlistItem
from src.domain.models.stock import Stock
from src.domain.services_interfaces.i_watchlist_repo import IWatchlistRepository
from src.domain.services_interfaces.i_stock_repo import IStockRepository


class WatchlistService:
    """
    Watchlist iş mantığı servisi.
    Watchlist CRUD işlemleri ve hisse ekleme/çıkarma işlemlerini yönetir.
    """

    def __init__(
        self,
        watchlist_repo: IWatchlistRepository,
        stock_repo: IStockRepository,
    ) -> None:
        self._watchlist_repo = watchlist_repo
        self._stock_repo = stock_repo

    # ---------- Watchlist operasyonları ---------- #

    def get_all_watchlists(self) -> List[Watchlist]:
        """Tüm watchlist'leri döner."""
        return self._watchlist_repo.get_all_watchlists()

    def get_watchlist_by_id(self, watchlist_id: int) -> Optional[Watchlist]:
        """Belirli bir watchlist'i id ile getirir."""
        return self._watchlist_repo.get_watchlist_by_id(watchlist_id)

    def create_watchlist(self, name: str, description: Optional[str] = None) -> Watchlist:
        """
        Yeni bir watchlist oluşturur.
        
        Args:
            name: Watchlist adı
            description: Opsiyonel açıklama
            
        Returns:
            Oluşturulan Watchlist objesi
        """
        if not name or not name.strip():
            raise ValueError("Watchlist adı boş olamaz")

        watchlist = Watchlist(
            id=None,
            name=name.strip(),
            description=description.strip() if description else None,
        )
        return self._watchlist_repo.create_watchlist(watchlist)

    def update_watchlist(
        self,
        watchlist_id: int,
        name: str,
        description: Optional[str] = None,
    ) -> None:
        """
        Var olan bir watchlist'i günceller.
        
        Args:
            watchlist_id: Güncellenecek watchlist id
            name: Yeni ad
            description: Yeni açıklama
        """
        if not name or not name.strip():
            raise ValueError("Watchlist adı boş olamaz")

        existing = self._watchlist_repo.get_watchlist_by_id(watchlist_id)
        if existing is None:
            raise ValueError(f"Watchlist bulunamadı: {watchlist_id}")

        updated_watchlist = Watchlist(
            id=watchlist_id,
            name=name.strip(),
            description=description.strip() if description else None,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
        )
        self._watchlist_repo.update_watchlist(updated_watchlist)

    def delete_watchlist(self, watchlist_id: int) -> None:
        """
        Watchlist'i siler. İçindeki tüm item'lar da silinir (CASCADE).
        
        Args:
            watchlist_id: Silinecek watchlist id
        """
        self._watchlist_repo.delete_watchlist(watchlist_id)

    # ---------- WatchlistItem operasyonları ---------- #

    def get_watchlist_stocks(
        self,
        watchlist_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Watchlist içindeki hisseleri detaylı bilgileriyle döner.
        
        Args:
            watchlist_id: Watchlist id
            
        Returns:
            Her hisse için dict: {item, stock, ticker, name}
        """
        items = self._watchlist_repo.get_items_by_watchlist_id(watchlist_id)
        
        if not items:
            return []

        stock_ids = [item.stock_id for item in items]
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {s.id: s for s in stocks}

        result = []
        for item in items:
            stock = stock_map.get(item.stock_id)
            result.append({
                "item": item,
                "stock": stock,
                "ticker": stock.ticker if stock else "?",
                "name": stock.name if stock else "Bilinmeyen Hisse",
            })

        return result

    def add_stock_to_watchlist(
        self,
        watchlist_id: int,
        stock_id: int,
        notes: Optional[str] = None,
    ) -> WatchlistItem:
        """
        Watchlist'e hisse ekler.
        
        Args:
            watchlist_id: Watchlist id
            stock_id: Eklenecek stock id
            notes: Opsiyonel not
            
        Returns:
            Oluşturulan WatchlistItem
            
        Raises:
            ValueError: Hisse zaten listede varsa
        """
        # Watchlist var mı kontrol et
        watchlist = self._watchlist_repo.get_watchlist_by_id(watchlist_id)
        if watchlist is None:
            raise ValueError(f"Watchlist bulunamadı: {watchlist_id}")

        # Stock var mı kontrol et
        stock = self._stock_repo.get_stock_by_id(stock_id)
        if stock is None:
            raise ValueError(f"Hisse bulunamadı: {stock_id}")

        # Zaten listede mi kontrol et
        if self._watchlist_repo.is_stock_in_watchlist(watchlist_id, stock_id):
            raise ValueError(f"Bu hisse zaten listede mevcut: {stock.ticker}")

        item = WatchlistItem(
            id=None,
            watchlist_id=watchlist_id,
            stock_id=stock_id,
            notes=notes.strip() if notes else None,
        )
        return self._watchlist_repo.add_item_to_watchlist(item)

    def add_stock_by_ticker(
        self,
        watchlist_id: int,
        ticker: str,
        notes: Optional[str] = None,
    ) -> WatchlistItem:
        """
        Ticker ile watchlist'e hisse ekler. Hisse yoksa önce oluşturur.
        
        Args:
            watchlist_id: Watchlist id
            ticker: Hisse ticker sembolü
            notes: Opsiyonel not
            
        Returns:
            Oluşturulan WatchlistItem
        """
        if not ticker or not ticker.strip():
            raise ValueError("Ticker boş olamaz")

        ticker = ticker.strip().upper()
        if "." not in ticker:
            ticker = ticker + ".IS"

        # Stock'u bul veya oluştur
        stock = self._stock_repo.get_stock_by_ticker(ticker)
        if stock is None:
            # Yeni stock oluştur
            new_stock = Stock(
                id=None,
                ticker=ticker,
                name=ticker,
                currency_code="TRY",
            )
            stock = self._stock_repo.insert_stock(new_stock)

        return self.add_stock_to_watchlist(watchlist_id, stock.id, notes)

    def remove_stock_from_watchlist(self, watchlist_id: int, stock_id: int) -> None:
        """
        Watchlist'ten hisseyi çıkarır.
        
        Args:
            watchlist_id: Watchlist id
            stock_id: Çıkarılacak stock id
        """
        self._watchlist_repo.remove_stock_from_watchlist(watchlist_id, stock_id)

    def get_watchlist_item_count(self, watchlist_id: int) -> int:
        """Watchlist'teki hisse sayısını döner."""
        items = self._watchlist_repo.get_items_by_watchlist_id(watchlist_id)
        return len(items)
