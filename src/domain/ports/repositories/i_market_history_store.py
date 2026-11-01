from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Sequence, Tuple

from src.domain.models.market_bar import MarketBar


class IMarketHistoryStore(ABC):
    """Tüm BIST piyasa geçmişinin yazma tarafı (artımlı senkron). Okuma: `IMarketHistoryRepository`."""

    @abstractmethod
    def exists(self) -> bool:
        """Depo dosyası var mı (yoksa senkron "veri yok" durumuna düşer)."""

    @abstractmethod
    def last_bar_date(self) -> Optional[date]:
        """Hisse kataloğundaki en son bar tarihi."""

    @abstractmethod
    def list_tickers(self) -> List[str]: ...

    @abstractmethod
    def invalid_bars(self, start: date, end: date) -> Tuple[Optional[date], int, List[Tuple[str, date]]]:
        """Aralıktaki kapanışı NULL/<=0 barlar: (en eski tarih, sayı, ilk 10 örnek)."""

    @abstractmethod
    def write_bars(self, bars: Sequence[MarketBar]) -> None:
        """Barları ekler/değiştirir, geçersiz kapanışları atar ve katalog istatistiklerini günceller."""

    @abstractmethod
    def bars_after(self, after: date, tickers: Sequence[str]) -> List[MarketBar]:
        """`after` tarihinden sonraki geçerli kapanışlı barlar (yalnızca verilen hisseler)."""


class IMarketBarDownloader(ABC):
    """Dış kaynaktan (yfinance) günlük BIST barı indirir."""

    @abstractmethod
    def download_daily(
        self, tickers: Sequence[str], start: date, end_exclusive: date
    ) -> Tuple[List[MarketBar], int, List[str]]:
        """(barlar, bar gelen hisse sayısı, hata mesajları)."""
