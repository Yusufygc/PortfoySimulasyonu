"""
StockLookupService — arayüz denetleyicileri için salt okunur hisse ve fiyat sorguları.

Denetleyiciler repository'lere doğrudan erişmez (UI -> Application -> Infrastructure). Bu servis
SQLite'taki hisse kayıtlarını (portföy, izleme listesi), günlük kapanışları ve canlı fiyat önbelleğini
tek bir okuma yüzeyi olarak sunar. Her sorgu hata durumunda boş sonuç döner; çağıran bir yedek yola geçebilir.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from src.domain.models.daily_price import DailyPrice
from src.domain.models.latest_price import LatestPrice
from src.domain.models.market_bar import MarketBar
from src.domain.models.stock import Stock
from src.domain.ticker import clean_ticker
from src.domain.market_clock import market_today

logger = logging.getLogger(__name__)


class StockLookupService:
    def __init__(self, stock_repo, price_repo, latest_price_repo, market_history_repo=None, price_lookup_service=None) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._latest_price_repo = latest_price_repo
        self._market_history_repo = market_history_repo
        self._price_lookup_service = price_lookup_service

    # --- Hisse kayıtları ---

    def get_stock(self, stock_id: int) -> Optional[Stock]:
        try:
            return self._stock_repo.get_stock_by_id(stock_id)
        except Exception as exc:
            logger.debug("Hisse okunamadı (id=%s): %s", stock_id, exc)
            return None

    def get_stocks(self, stock_ids: Sequence[int]) -> Dict[int, Stock]:
        """Tek toplu sorguyla {stock_id: Stock}; bulunamayan id sonuçta yer almaz."""
        ids = [sid for sid in dict.fromkeys(stock_ids) if sid is not None]
        if not ids:
            return {}
        try:
            return {stock.id: stock for stock in self._stock_repo.get_stocks_by_ids(ids)}
        except Exception as exc:
            logger.debug("Toplu hisse bilgisi alınamadı: %s", exc)
            return {}

    def find_stock(self, ticker: str) -> Optional[Stock]:
        """`THYAO` ve `THYAO.IS` aynı kaydı bulur (depo `.IS` son ekini tolere eder)."""
        try:
            return self._stock_repo.get_stock_by_ticker(ticker)
        except Exception as exc:
            logger.debug("Hisse bulunamadı (%s): %s", ticker, exc)
            return None

    def is_known_ticker(self, ticker: str) -> bool:
        """Ağ çağrısı yapmadan: SQLite'ta kayıtlı veya DuckDB piyasa kataloğunda (tüm BIST) var mı?"""
        code = clean_ticker(ticker)
        if not code:
            return False
        if self.find_stock(code) is not None:
            return True
        if self._market_history_repo is None:
            return False
        try:
            return bool(self._market_history_repo.has_ticker(code))
        except Exception as exc:
            logger.debug("DuckDB katalog sorgusu başarısız (%s): %s", code, exc)
            return False

    def verify_ticker_online(self, ticker: str) -> bool:
        """Çevrimiçi fiyat sorgusu fiyat döndürüyorsa kod geçerlidir (yavaş; arka planda çağrılmalı)."""
        if self._price_lookup_service is None:
            return False
        try:
            return self._price_lookup_service.lookup_price_for_ticker(ticker) is not None
        except Exception as exc:
            logger.debug("Çevrimiçi kod doğrulaması başarısız (%s): %s", ticker, exc)
            return False

    def list_stocks(self) -> List[Stock]:
        try:
            return list(self._stock_repo.get_all_stocks())
        except Exception as exc:
            logger.debug("Hisse listesi alınamadı: %s", exc)
            return []

    # --- Günlük fiyatlar ---

    def get_price_series(self, stock_id: int, start_date: date, end_date: date) -> List[DailyPrice]:
        try:
            return list(self._price_repo.get_price_series(stock_id, start_date, end_date))
        except Exception as exc:
            logger.debug("Fiyat serisi okunamadı (id=%s): %s", stock_id, exc)
            return []

    def get_price_series_bulk(self, stock_ids: Sequence[int], start_date: date, end_date: date) -> Dict[int, List[DailyPrice]]:
        ids = [sid for sid in dict.fromkeys(stock_ids) if sid is not None]
        if not ids:
            return {}
        try:
            return self._price_repo.get_price_series_bulk(ids, start_date, end_date)
        except Exception as exc:
            logger.warning("Toplu fiyat serisi alınamadı: %s", exc)
            return {}

    def get_previous_close(self, stock_id: int, before: Optional[date] = None) -> Optional[Decimal]:
        """`before` gününden (varsayılan bugün) önceki son kapanış; yoksa None."""
        try:
            price = self._price_repo.get_last_price_before(stock_id, before or market_today())
        except Exception as exc:
            logger.debug("Önceki kapanış okunamadı (id=%s): %s", stock_id, exc)
            return None
        close = getattr(price, "close_price", None) if price else None
        return close if close and close > 0 else None

    def get_latest_close(self, ticker: str) -> Optional[Decimal]:
        """Ticker için SQLite'taki en güncel kapanış (hisse kayıtlı değilse None)."""
        stock = self.find_stock(ticker)
        if stock is None:
            return None
        return self.get_previous_close(stock.id, date.max)

    # --- Canlı fiyat önbelleği ---

    def get_latest_price_map(self, stock_ids: Sequence[int]) -> Dict[int, Decimal]:
        ids = [sid for sid in dict.fromkeys(stock_ids) if sid is not None]
        if not ids:
            return {}
        try:
            return dict(self._latest_price_repo.get_latest_price_map(ids))
        except Exception as exc:
            logger.debug("Canlı fiyat haritası alınamadı: %s", exc)
            return {}

    def get_latest_prices(self, stock_ids: Sequence[int]) -> Dict[int, LatestPrice]:
        """Canlı fiyat önbelleği kayıtları (fiyat, zaman damgası, kaynak); okunamazsa boş."""
        ids = [sid for sid in dict.fromkeys(stock_ids) if sid is not None]
        if not ids:
            return {}
        try:
            return dict(self._latest_price_repo.get_latest_prices(ids))
        except Exception as exc:
            logger.debug("Canlı fiyat kayıtları alınamadı: %s", exc)
            return {}

    # --- DuckDB piyasa geçmişi (tüm BIST, düzeltilmiş fiyatlar) ---

    def get_market_bars(self, ticker: str, start_date: date, end_date: date) -> List[MarketBar]:
        if self._market_history_repo is None:
            return []
        try:
            return list(self._market_history_repo.get_price_series(clean_ticker(ticker), start_date, end_date))
        except Exception as exc:
            logger.warning("DuckDB fiyat verisi okunamadı (%s): %s", ticker, exc)
            return []

    def get_last_market_bars(self, ticker: str, count: int) -> List[MarketBar]:
        """En yeni çubuk ilk sırada olacak şekilde son `count` geçerli kapanış."""
        if self._market_history_repo is None:
            return []
        try:
            return list(self._market_history_repo.get_last_bars(clean_ticker(ticker), count))
        except Exception as exc:
            logger.debug("DuckDB son çubuklar okunamadı (%s): %s", ticker, exc)
            return []

    def get_market_company_name(self, ticker: str) -> Optional[str]:
        if self._market_history_repo is None:
            return None
        try:
            return self._market_history_repo.get_company_name(clean_ticker(ticker)) or None
        except Exception as exc:
            logger.debug("DuckDB şirket adı okunamadı (%s): %s", ticker, exc)
            return None
