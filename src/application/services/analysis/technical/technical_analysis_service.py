"""
TechnicalAnalysisService — Golden / Death Cross orkestrasyonu.

Sorumluluk:
- Tüm BIST tickerleri için kapanış serilerini DB'den oku
- detect_crosses (saf) ile cross olaylarını çıkar
- Idempotent upsert ile golden_cross_events tablosuna yaz
- UI'a recent / per-ticker query API'leri sağla
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd

from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent
from src.domain.models.stock import Stock
from src.domain.ports.repositories.i_golden_cross_repo import IGoldenCrossRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.application.services.analysis.technical.golden_cross import (
    DetectedCross,
    detect_crosses,
)

logger = logging.getLogger(__name__)

_DEFAULT_SHORT = 50
_DEFAULT_LONG  = 200
# detect için min 1 yıllık veri (long + buffer); CSV import ile 10y var.
_LOOKBACK_YEARS = 10


@dataclass(frozen=True)
class ScanResult:
    scanned_count: int
    new_event_count: int
    skipped_count: int  # yetersiz veri


class TechnicalAnalysisService:
    """EMA50/EMA200 cross taraması — tüm BIST veya tek ticker."""

    def __init__(
        self,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        golden_cross_repo: IGoldenCrossRepository,
        short_period: int = _DEFAULT_SHORT,
        long_period:  int = _DEFAULT_LONG,
    ) -> None:
        self._price_repo  = price_repo
        self._stock_repo  = stock_repo
        self._cross_repo  = golden_cross_repo
        self._short       = short_period
        self._long        = long_period

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan_all(self, today: Optional[date] = None) -> ScanResult:
        """Tüm BIST tickerleri için cross taraması, yeni eventleri DB'ye yaz."""
        today = today or date.today()
        stocks = self._stock_repo.get_all_stocks()
        logger.info("Golden Cross taraması başlıyor: %d ticker", len(stocks))

        total_new   = 0
        skipped     = 0
        all_events: list[GoldenCrossEvent] = []

        for stock in stocks:
            if stock.id is None:
                continue
            events = self._scan_single(stock, today)
            if events is None:
                skipped += 1
                continue
            all_events.extend(events)

        if all_events:
            total_new = self._cross_repo.upsert_events_bulk(all_events)
        logger.info(
            "Golden Cross taraması tamamlandı: %d ticker, %d yeni event, %d atlandı (yetersiz veri)",
            len(stocks), total_new, skipped,
        )
        return ScanResult(scanned_count=len(stocks), new_event_count=total_new, skipped_count=skipped)

    def scan_ticker(self, ticker: str, today: Optional[date] = None) -> ScanResult:
        """Tek ticker için tam tarama."""
        today = today or date.today()
        stock = self._stock_repo.get_stock_by_ticker(ticker.strip().upper())
        if stock is None or stock.id is None:
            return ScanResult(scanned_count=0, new_event_count=0, skipped_count=0)
        events = self._scan_single(stock, today)
        if events is None:
            return ScanResult(scanned_count=1, new_event_count=0, skipped_count=1)
        new_count = self._cross_repo.upsert_events_bulk(events)
        return ScanResult(scanned_count=1, new_event_count=new_count, skipped_count=0)

    def _scan_single(self, stock: Stock, today: date) -> Optional[List[GoldenCrossEvent]]:
        """Tek stock için detect + GoldenCrossEvent listesi üret. None → yetersiz veri."""
        start = today - timedelta(days=int(_LOOKBACK_YEARS * 365.25))
        series_rows = self._price_repo.get_price_series(stock.id, start, today)
        if not series_rows or len(series_rows) < self._long + 1:
            return None
        ser = pd.Series(
            data=[float(r.close_price) for r in series_rows],
            index=[r.price_date for r in series_rows],
        ).sort_index()
        detected = detect_crosses(ser, short=self._short, long=self._long)
        return [self._to_event(stock, d) for d in detected]

    def _to_event(self, stock: Stock, det: DetectedCross) -> GoldenCrossEvent:
        return GoldenCrossEvent(
            id=None,
            stock_id=stock.id,  # type: ignore[arg-type]
            ticker=stock.ticker,
            cross_date=det.cross_date,
            cross_type=det.cross_type,
            short_ma=det.short_ma,
            long_ma=det.long_ma,
            close_price=det.close_price,
        )

    # ------------------------------------------------------------------
    # Queries (UI için)
    # ------------------------------------------------------------------

    def get_recent_events(
        self,
        days: int = 30,
        cross_type: Optional[CrossType] = None,
        limit: int = 200,
    ) -> List[GoldenCrossEvent]:
        since = date.today() - timedelta(days=days)
        return self._cross_repo.get_recent_events(since=since, cross_type=cross_type, limit=limit)

    def get_events_for_ticker(self, ticker: str) -> List[GoldenCrossEvent]:
        stock = self._stock_repo.get_stock_by_ticker(ticker.strip().upper())
        if stock is None or stock.id is None:
            return []
        return self._cross_repo.get_events_for_stock(stock.id)
