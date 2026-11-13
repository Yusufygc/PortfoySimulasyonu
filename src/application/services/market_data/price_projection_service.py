"""SQLite `daily_prices` = DuckDB piyasa geçmişinin yansıması (tek fiyat kaynağı).

Fiyatın sahibi DuckDB'dir (ham bar + onaylı kurumsal aksiyon faktörü, okuma anında). SQLite yalnızca takip edilen
hisseler (`stocks` tablosu) için bu düzeltilmiş serinin kopyasını tutar; portföy değerlemesi ve analiz SQLite'tan
okur. SQLite'a fiyat yazan TEK yer bu servistir (`tests/test_price_single_writer_guard.py`).

Kural:
- DuckDB'deki hayalet bar (tatil, hacimsiz sabit fiyat) ve hacmi 0 olan bar yansıtılmaz.
- Aralıkta DuckDB'de bulunmayan SQLite günleri silinir (eski/bozuk kopya kalmaz).
- DuckDB'de hiç barı olmayan hissenin SQLite fiyatlarına dokunulmaz (raporlanır; kaynak indirmesi gerekir).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from src.domain.market_clock import market_today
from src.domain.models.daily_price import DailyPrice
from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository

logger = logging.getLogger(__name__)

EARLIEST = date(2000, 1, 1)
SOURCE = "duckdb"


@dataclass
class ProjectionResult:
    written: Dict[int, int] = field(default_factory=dict)        # stock_id -> yazılan/güncellenen satır
    deleted: Dict[int, int] = field(default_factory=dict)        # stock_id -> silinen eski satır
    last_prices: Dict[int, Decimal] = field(default_factory=dict)
    missing: List[str] = field(default_factory=list)            # DuckDB'de barı olmayan hisseler

    @property
    def written_count(self) -> int:
        return sum(self.written.values())


def _dec(value) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value))


STORED_PRICE_STEP = 0.0001  # SQLite fiyat sütunları 4 haneyle saklanır (ExactNumeric(18, 4))


def _same(a, b) -> bool:
    """Depolama hassasiyetinde eşit mi (DuckDB float32 kalıntısı ve 4 haneye yuvarlama fark sayılmaz)."""
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= STORED_PRICE_STEP / 2 + 1e-9


def _differs(stored: Optional[DailyPrice], bar: MarketBar) -> bool:
    if stored is None:
        return True
    pairs = ((stored.close_price, bar.close_price), (stored.open_price, bar.open_price),
             (stored.high_price, bar.high_price), (stored.low_price, bar.low_price))
    return not all(_same(a, b) for a, b in pairs) or stored.volume != bar.volume or stored.source != SOURCE


def _usable(bar: MarketBar, is_ghost) -> bool:
    if not bar.close_price or bar.close_price <= 0 or bar.volume == 0:
        return False
    return not is_ghost(bar)


class PriceProjectionService:
    def __init__(
        self,
        history_repo: IMarketHistoryRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        ghost_filter=None,
    ) -> None:
        """`ghost_filter(bar) -> bool` hayalet bar kuralı (altyapıdaki `bar_quality`); verilmezse yalnızca hacim 0 elenir."""
        self._history = history_repo
        self._prices = price_repo
        self._stocks = stock_repo
        self._is_ghost = ghost_filter or (lambda _bar: False)

    def project(
        self,
        stock_ids: Optional[Sequence[int]] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> ProjectionResult:
        """Verilen (yoksa tüm takip edilen) hisselerin aralıktaki SQLite fiyatlarını DuckDB'den eşitler.

        Toplu okuma (tek DuckDB bağlantısı, tek SQLite sorgusu) yapar ve yalnızca farklı satırları yazar; değişiklik
        yoksa yazma olmaz (her senkronda çağrılabilir)."""
        start, end = start or EARLIEST, end or market_today()
        tickers = self._selected_tickers(stock_ids)
        result = ProjectionResult()
        if not tickers:
            return result
        bars_by_ticker = self._history.get_price_series_bulk(sorted(set(tickers.values())), start, end)
        stored_by_id = self._prices.get_price_series_bulk(sorted(tickers), start, end)
        for stock_id, ticker in tickers.items():
            bars = [b for b in bars_by_ticker.get(ticker, []) if _usable(b, self._is_ghost)]
            self._sync_stock(stock_id, ticker, bars, stored_by_id.get(stock_id, []), result)
        if result.written or result.deleted:
            logger.info("Fiyat yansıtması: %d satır yazıldı, %d eski satır silindi (%d hisse)",
                        result.written_count, sum(result.deleted.values()), len(tickers))
        return result

    def _selected_tickers(self, stock_ids: Optional[Sequence[int]]) -> Dict[int, str]:
        wanted = None if stock_ids is None else {int(s) for s in stock_ids}
        return {
            stock.id: (stock.ticker or "").strip().upper().replace(".IS", "")
            for stock in self._stocks.get_all_stocks()
            if stock.id is not None and (wanted is None or stock.id in wanted)
        }

    def _sync_stock(self, stock_id: int, ticker: str, bars, stored, result: ProjectionResult) -> None:
        if not bars:
            if not self._history.get_last_bars(ticker, 1):
                result.missing.append(ticker)
            return
        current = {p.price_date: p for p in stored}
        written = self._write_changes(stock_id, bars, current)
        deleted = self._delete_stale(stock_id, bars, current)
        if written:
            result.written[stock_id] = written
        if deleted:
            result.deleted[stock_id] = deleted
        result.last_prices[stock_id] = _dec(bars[-1].close_price)

    def _write_changes(self, stock_id: int, bars, current: dict) -> int:
        changed = [b for b in bars if _differs(current.get(b.price_date), b)]
        if changed:
            self._prices.upsert_daily_prices_bulk([self._to_price(stock_id, bar) for bar in changed])
        return len(changed)

    def _delete_stale(self, stock_id: int, bars, current: dict) -> int:
        """DuckDB serisinin kapsadığı aralıkta DuckDB'de olmayan SQLite günleri (eski/bozuk kopya)."""
        kept = {b.price_date for b in bars}
        first, last = bars[0].price_date, bars[-1].price_date
        stale = [day for day in current if first <= day <= last and day not in kept]
        return self._prices.delete_prices_for_dates(stock_id, stale) if stale else 0

    @staticmethod
    def _to_price(stock_id: int, bar: MarketBar) -> DailyPrice:
        return DailyPrice(
            id=None, stock_id=stock_id, price_date=bar.price_date, close_price=_dec(bar.close_price),
            currency_code="TRY", source=SOURCE, open_price=_dec(bar.open_price), high_price=_dec(bar.high_price),
            low_price=_dec(bar.low_price), volume=bar.volume,
        )
