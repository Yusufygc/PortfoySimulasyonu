"""
ScreenerService — BIST çoklu sinyal tarayıcısı orkestrasyonu.

Sorumluluk:
- Tüm (veya seçili) BIST hisseleri için OHLCV serilerini local DB'den oku
- build_snapshot (saf) ile indikatör anlık görüntüsünü çıkar
- SCREENER_FILTERS'daki hazır filtrelerle eşleştir, ScreenerMatch listesi döndür

Zorunlu bağımlılık (bkz. TRANSFORMATION_PLAN.md §9.6): Bu servis SADECE
price_repo üzerinden yerel DB'yi okur — canlı YFinance/API çağrısı yapmaz.
"Saniyeler içinde tarama" hedefi bu önkoşula bağlıdır.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd

from src.application.services.analysis.technical.screener import (
    SCREENER_FILTERS,
    IndicatorSnapshot,
    build_snapshot,
)
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository

logger = logging.getLogger(__name__)

# EMA200'ün güvenilir converge etmesi için ~1.15 yıllık ısınma payı.
_DEFAULT_LOOKBACK_DAYS = 420


@dataclass(frozen=True)
class ScreenerMatch:
    """scan() dönüş değeri — pure veri (DB yok)."""
    ticker: str
    filter_key: str
    filter_label: str
    close_price: float


def _rows_to_series(rows: List[DailyPrice], field: str) -> pd.Series:
    dates = [r.price_date for r in rows]
    values = [float(getattr(r, field)) if getattr(r, field) is not None else float("nan") for r in rows]
    return pd.Series(values, index=dates)


class ScreenerService:
    """Hazır stratejilerle tüm BIST hisselerini yerel cache üzerinden tarar."""

    def __init__(
        self,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._lookback_days = lookback_days

    def scan(
        self,
        filter_keys: Optional[List[str]] = None,
        today: Optional[date] = None,
    ) -> List[ScreenerMatch]:
        """Verilen filtre anahtarlarıyla (None → tüm filtreler) tüm hisseleri tarar."""
        keys = filter_keys if filter_keys is not None else list(SCREENER_FILTERS.keys())
        today = today or date.today()
        start = today - timedelta(days=self._lookback_days)

        matches: List[ScreenerMatch] = []
        for stock in self._stock_repo.get_all_stocks():
            if stock.id is None:
                continue
            snapshot = self._build_snapshot_for_stock(stock, start, today)
            if snapshot is None:
                continue
            matches.extend(self._matches_for_snapshot(stock.ticker, snapshot, keys))
        return matches

    def scan_ticker(self, ticker: str, filter_keys: Optional[List[str]] = None, today: Optional[date] = None) -> List[ScreenerMatch]:
        """Tek ticker için tarama (UI'da tek hisse detay kontrolü için)."""
        stock = self._stock_repo.get_stock_by_ticker(ticker.strip().upper())
        if stock is None or stock.id is None:
            return []
        keys = filter_keys if filter_keys is not None else list(SCREENER_FILTERS.keys())
        today = today or date.today()
        start = today - timedelta(days=self._lookback_days)
        snapshot = self._build_snapshot_for_stock(stock, start, today)
        if snapshot is None:
            return []
        return self._matches_for_snapshot(stock.ticker, snapshot, keys)

    def _build_snapshot_for_stock(self, stock: Stock, start: date, end: date) -> Optional[IndicatorSnapshot]:
        rows = self._price_repo.get_price_series(stock.id, start, end)
        if not rows:
            return None
        return build_snapshot(
            closes=_rows_to_series(rows, "close_price"),
            highs=_rows_to_series(rows, "high_price"),
            lows=_rows_to_series(rows, "low_price"),
            volumes=_rows_to_series(rows, "volume"),
        )

    @staticmethod
    def _matches_for_snapshot(ticker: str, snapshot: IndicatorSnapshot, keys: List[str]) -> List[ScreenerMatch]:
        results: List[ScreenerMatch] = []
        for key in keys:
            filter_def = SCREENER_FILTERS.get(key)
            if filter_def is None:
                logger.warning("Tanımsız screener filtre anahtarı: %s", key)
                continue
            if filter_def.predicate(snapshot):
                results.append(ScreenerMatch(
                    ticker=ticker,
                    filter_key=key,
                    filter_label=filter_def.label,
                    close_price=snapshot.close,
                ))
        return results
