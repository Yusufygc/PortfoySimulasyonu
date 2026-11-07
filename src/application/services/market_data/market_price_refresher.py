"""Hisse fiyatlarını kaynaktan indirip DuckDB'ye yazar ve SQLite yansımasını günceller (tek yazma yolu).

Fiyat sağlığı ("eksikleri tamamla"), backfill ve kurumsal aksiyon sonrası yeniden indirme bu servisi kullanır;
böylece SQLite'a hiçbir yerden doğrudan fiyat yazılmaz.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Sequence

from src.domain.models.stock import Stock
from src.domain.ports.repositories.i_market_history_store import IMarketBarDownloader, IMarketHistoryStore


@dataclass
class RefreshResult:
    updated: Dict[int, int] = field(default_factory=dict)       # stock_id -> SQLite'a yazılan satır
    last_prices: Dict[int, Decimal] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    downloaded_bars: int = 0

    @property
    def updated_count(self) -> int:
        return sum(self.updated.values())


def _clean(ticker: str) -> str:
    return (ticker or "").strip().upper().replace(".IS", "")


class MarketPriceRefresher:
    def __init__(self, downloader: IMarketBarDownloader | None, store: IMarketHistoryStore, projection) -> None:
        self._downloader = downloader
        self._store = store
        self._projection = projection

    def refresh(self, stocks: Sequence[Stock], start: date, end: date) -> RefreshResult:
        """`[start, end]` aralığını indirir (DuckDB), sonra aynı aralığı SQLite'a yansıtır."""
        result = RefreshResult()
        targets = [s for s in stocks if s.id is not None and _clean(s.ticker)]
        if not targets or start > end:
            return result
        self._download(targets, (start, end), result)
        projected = self._projection.project([s.id for s in targets], start, end)
        result.updated = dict(projected.written)
        result.last_prices = {sid: price for sid, price in projected.last_prices.items()}
        return result

    def _download(self, targets: Sequence[Stock], window, result: RefreshResult) -> None:
        if self._downloader is None:
            result.errors.append("Piyasa verisi indiricisi yok.")
            return
        start, end = window
        tickers = sorted({_clean(s.ticker) for s in targets})
        bars, _count, errors = self._downloader.download_daily(tickers, start, end + timedelta(days=1))
        result.errors.extend(errors)
        if bars:
            self._store.write_bars(bars)
            result.downloaded_bars = len(bars)

    def delete_range(self, stocks: Sequence[Stock], start: date, end: date) -> int:
        """Bakım: aralıktaki barları DuckDB'den siler (SQLite yansıması çağıran tarafından silinir)."""
        return self._store.delete_range([_clean(s.ticker) for s in stocks if s.ticker], start, end)
