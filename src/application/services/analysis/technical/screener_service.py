"""
ScreenerService — BIST çoklu sinyal tarayıcısı orkestrasyonu.

Sorumluluk:
- Tüm BIST hisseleri (DuckDB piyasa geçmişi, sermaye artırımı düzeltmeli) için OHLCV serilerini yerel depodan oku
- build_snapshot (saf) ile indikatör anlık görüntüsünü çıkar
- SCREENER_FILTERS'daki hazır filtrelerle eşleştir, ScreenerMatch listesi döndür

Zorunlu bağımlılık (bkz. TRANSFORMATION_PLAN.md §9.6): Bu servis SADECE yerel DuckDB'yi okur —
canlı YFinance/API çağrısı yapmaz. "Saniyeler içinde tarama" hedefi bu önkoşula bağlıdır.
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
from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository

logger = logging.getLogger(__name__)

# EMA200'ün güvenilir converge etmesi için ~1.15 yıllık ısınma payı.
_DEFAULT_LOOKBACK_DAYS = 420
_SCAN_CHUNK = 100  # tek sorguda okunan hisse sayısı


@dataclass(frozen=True)
class ScreenerMatch:
    """scan() dönüş değeri — pure veri (DB yok)."""
    ticker: str
    filter_key: str
    filter_label: str
    close_price: float


def _bars_to_series(bars: List[MarketBar], field: str) -> pd.Series:
    dates = [b.price_date for b in bars]
    values = [float(getattr(b, field)) if getattr(b, field) is not None else float("nan") for b in bars]
    return pd.Series(values, index=dates)


class ScreenerService:
    """Hazır stratejilerle tüm BIST hisselerini yerel DuckDB üzerinden tarar."""

    def __init__(
        self,
        market_history_repo: IMarketHistoryRepository,
        lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
    ) -> None:
        self._history = market_history_repo
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

        tickers = self._history.list_tickers()
        matches: List[ScreenerMatch] = []
        for offset in range(0, len(tickers), _SCAN_CHUNK):
            chunk = tickers[offset:offset + _SCAN_CHUNK]
            for ticker, bars in self._history.get_price_series_bulk(chunk, start, today).items():
                snapshot = self._build_snapshot(bars)
                if snapshot is not None:
                    matches.extend(self._matches_for_snapshot(ticker, snapshot, keys))
        return matches

    def scan_ticker(self, ticker: str, filter_keys: Optional[List[str]] = None, today: Optional[date] = None) -> List[ScreenerMatch]:
        """Tek ticker için tarama (UI'da tek hisse detay kontrolü için)."""
        clean = (ticker or "").strip().upper().replace(".IS", "")
        keys = filter_keys if filter_keys is not None else list(SCREENER_FILTERS.keys())
        today = today or date.today()
        start = today - timedelta(days=self._lookback_days)
        snapshot = self._build_snapshot(self._history.get_price_series(clean, start, today))
        if snapshot is None:
            return []
        return self._matches_for_snapshot(clean, snapshot, keys)

    @staticmethod
    def _build_snapshot(bars: List[MarketBar]) -> Optional[IndicatorSnapshot]:
        if not bars:
            return None
        return build_snapshot(
            closes=_bars_to_series(bars, "close_price"),
            highs=_bars_to_series(bars, "high_price"),
            lows=_bars_to_series(bars, "low_price"),
            volumes=_bars_to_series(bars, "volume"),
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
