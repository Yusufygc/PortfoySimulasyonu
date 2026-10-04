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
from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_golden_cross_repo import IGoldenCrossRepository
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository
from src.application.services.analysis.technical.golden_cross import (
    DetectedCross,
    detect_crosses,
)
from src.domain.market_clock import market_today

logger = logging.getLogger(__name__)

_DEFAULT_SHORT = 50
_MAX_PRICE_RATIO = 1000.0  # medyandan bu kadar sapan fiyat → bozuk veri
_SCAN_CHUNK = 60  # tek sorguda okunan hisse sayısı (bellek/tek bağlantı dengesi)


def _clean_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper().replace(".IS", "")


def _is_series_sane(ser: pd.Series, ticker: str, log: logging.Logger) -> bool:
    """Fiyat serisinde aşırı outlier var mı kontrol et.

    Medyandan 1000x daha yüksek veya düşük değerler bozuk veri işareti.
    Örnek: EREGL'de yanlış ölçekle girilmiş milyonluk fiyatlar.
    """
    median = ser.median()
    if median <= 0:
        log.warning("%s: medyan fiyat <= 0, atlanıyor.", ticker)
        return False
    ratio = ser.max() / median
    if ratio > _MAX_PRICE_RATIO:
        log.warning(
            "%s: fiyat aralığı şüpheli (max/median=%.1f), EMA hesabı atlanıyor.",
            ticker, ratio,
        )
        return False
    return True
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
        market_history_repo: IMarketHistoryRepository,
        golden_cross_repo: IGoldenCrossRepository,
        short_period: int = _DEFAULT_SHORT,
        long_period:  int = _DEFAULT_LONG,
    ) -> None:
        self._history     = market_history_repo
        self._cross_repo  = golden_cross_repo
        self._short       = short_period
        self._long        = long_period

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan_all(self, today: Optional[date] = None) -> ScanResult:
        """Tüm BIST (DuckDB piyasa geçmişi, düzeltilmiş fiyatlar) için cross taraması, yeni eventleri DB'ye yaz."""
        today = today or market_today()
        tickers = self._history.list_tickers()
        logger.info("Golden Cross taraması başlıyor: %d ticker", len(tickers))

        start = today - timedelta(days=int(_LOOKBACK_YEARS * 365.25))
        total_new = 0
        skipped = 0
        all_events: list[GoldenCrossEvent] = []

        for offset in range(0, len(tickers), _SCAN_CHUNK):
            chunk = tickers[offset:offset + _SCAN_CHUNK]
            series_by_ticker = self._history.get_price_series_bulk(chunk, start, today)
            for ticker in chunk:
                events = self._events_from_bars(ticker, series_by_ticker.get(ticker, []))
                if events is None:
                    skipped += 1
                    continue
                all_events.extend(events)

        if all_events:
            total_new = self._cross_repo.upsert_events_bulk(all_events)
        logger.info(
            "Golden Cross taraması tamamlandı: %d ticker, %d yeni event, %d atlandı (yetersiz veri)",
            len(tickers), total_new, skipped,
        )
        return ScanResult(scanned_count=len(tickers), new_event_count=total_new, skipped_count=skipped)

    def scan_ticker(self, ticker: str, today: Optional[date] = None) -> ScanResult:
        """Tek ticker için tam tarama."""
        today = today or market_today()
        clean = _clean_ticker(ticker)
        if not clean or not self._history.has_ticker(clean):
            return ScanResult(scanned_count=0, new_event_count=0, skipped_count=0)
        start = today - timedelta(days=int(_LOOKBACK_YEARS * 365.25))
        events = self._events_from_bars(clean, self._history.get_price_series(clean, start, today))
        if events is None:
            return ScanResult(scanned_count=1, new_event_count=0, skipped_count=1)
        new_count = self._cross_repo.upsert_events_bulk(events)
        return ScanResult(scanned_count=1, new_event_count=new_count, skipped_count=0)

    def _events_from_bars(self, ticker: str, bars: List[MarketBar]) -> Optional[List[GoldenCrossEvent]]:
        """Bir hissenin barlarından cross olayları. None → yetersiz/bozuk veri."""
        if not bars or len(bars) < self._long * 2:
            return None
        ser = pd.Series(
            data=[float(b.close_price) for b in bars],
            index=[b.price_date for b in bars],
        ).sort_index()
        if not _is_series_sane(ser, ticker, logger):
            return None
        detected = detect_crosses(ser, short=self._short, long=self._long)
        return [self._to_event(ticker, d) for d in detected]

    @staticmethod
    def _to_event(ticker: str, det: DetectedCross) -> GoldenCrossEvent:
        return GoldenCrossEvent(
            id=None,
            ticker=ticker,
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
        since = market_today() - timedelta(days=days)
        return self._cross_repo.get_recent_events(since=since, cross_type=cross_type, limit=limit)

    def get_events_for_ticker(self, ticker: str) -> List[GoldenCrossEvent]:
        return self._cross_repo.get_events_for_ticker(_clean_ticker(ticker))
