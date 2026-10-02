from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Optional, Sequence

from src.domain.models.market_bar import MarketBar


class IMarketHistoryRepository(ABC):
    """Tüm BIST için ticker bazlı, yalnızca okunur piyasa geçmişi (DuckDB OLAP katmanı).

    Portföy/işlem verisinin sahibi SQLite'tır; bu port yalnızca portföyde olmayan hisselerin de
    fiyat geçmişine (grafik, DCA, optimizasyon) erişmek içindir. Veri yoksa veya depo o anda
    kullanılamıyorsa boş sonuç döner, istisna fırlatmaz.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Piyasa geçmişi dosyası mevcut ve okunabilir mi."""
        raise NotImplementedError

    @abstractmethod
    def get_price_series(self, ticker: str, start_date: date, end_date: date) -> List[MarketBar]:
        """Tarih aralığındaki günlük barlar (eskiden yeniye). `.IS` uzantısı verilse de verilmese de çalışır."""
        raise NotImplementedError

    @abstractmethod
    def get_last_bars(self, ticker: str, count: int = 2) -> List[MarketBar]:
        """Geçerli kapanışı olan son `count` bar (yeniden eskiye)."""
        raise NotImplementedError

    @abstractmethod
    def has_ticker(self, ticker: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_company_name(self, ticker: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def list_tickers(self) -> List[str]:
        """Katalogdaki (bist_stocks) tüm tickerlar, uzantısız büyük harf, alfabetik."""
        raise NotImplementedError

    @abstractmethod
    def get_price_series_bulk(
        self, tickers: Sequence[str], start_date: date, end_date: date
    ) -> Dict[str, List[MarketBar]]:
        """Birden çok hisse için tek sorguda günlük barlar (ticker -> eskiden yeniye). Verisiz hisse sonuçta yer almaz."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_dates(self) -> Dict[str, date]:
        """Her hissenin geçerli kapanışlı son bar tarihi (ticker -> tarih)."""
        raise NotImplementedError
