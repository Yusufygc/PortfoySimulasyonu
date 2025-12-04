# src/domain/services_interfaces/i_portfolio_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, List, Optional, Sequence

from src.domain.models.trade import Trade


class IPortfolioRepository(ABC):
    """
    Portföy ile ilgili trade verilerine erişim için soyut arayüz.

    Amaç:
      - Uygulama/service katmanı bu interface'e göre programlar
      - MySQL/PostgreSQL/SQLite fark etmeksizin concrete repo bu interface'i uygular.
    """

    # --------- READ (Query) operasyonları --------- #

    @abstractmethod
    def get_all_trades(self) -> List[Trade]:
        """
        Tüm trade kayıtlarını döner.
        Küçük projede olur ama real hayatta pagination / filtre gerekebilir.
        """
        raise NotImplementedError

    @abstractmethod
    def get_trades_by_stock(self, stock_id: int) -> List[Trade]:
        """
        Belirli bir hisse için tüm trade'leri döner.
        """
        raise NotImplementedError

    @abstractmethod
    def get_trades_by_date_range(self, start_date: date, end_date: date) -> List[Trade]:
        """
        Belirtilen tarih aralığındaki tüm trade'leri döner.
        """
        raise NotImplementedError

    @abstractmethod
    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """
        Tek bir trade'i id üzerinden döner.
        Bulunamazsa None.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_stock_ids_in_portfolio(self) -> Sequence[int]:
        """
        Portföyde en az bir trade'i olan tüm hisselerin stock_id listesini döner.

        Gün sonu fiyat güncellemesi vs. yaparken:
          - Bu listeyi al
          - Her stock_id için yfinance'ten fiyat çek
        """
        raise NotImplementedError

    # --------- WRITE (Command) operasyonları --------- #

    @abstractmethod
    def insert_trade(self, trade: Trade) -> Trade:
        """
        Yeni bir trade kaydı ekler.

        Dönüş:
          - DB'nin ürettiği id ile birlikte Trade objesini geri döner
          (örn. trade.id dolu olarak).
        """
        raise NotImplementedError

    @abstractmethod
    def insert_trades_bulk(self, trades: Iterable[Trade]) -> None:
        """
        Birden fazla trade kaydını toplu insert etmek için opsiyonel metot.
        Performans gerektiğinde kullanılabilir.
        """
        raise NotImplementedError

    @abstractmethod
    def update_trade(self, trade: Trade) -> None:
        """
        Var olan bir trade kaydını günceller.
        (Kullanıcı yanlış lot/fiyat girdiyse düzeltme senaryoları için.)
        """
        raise NotImplementedError

    @abstractmethod
    def delete_trade(self, trade_id: int) -> None:
        """
        Trade kaydını siler.
        Dikkat: Gerçek hayatta "soft delete" daha mantıklı olabilir.
        """
        raise NotImplementedError
