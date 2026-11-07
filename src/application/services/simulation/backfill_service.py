"""Geçmişe yönelik fiyat verisi yönetimi: aralık indirme ve silme.

İndirme `MarketPriceRefresher` üzerinden yapılır: barlar DuckDB'ye (fiyatın sahibi) yazılır, SQLite `daily_prices`
yalnızca yansıtma ile güncellenir. Kurumsal aksiyon düzeltmesi DuckDB'nin onaylı faktörleriyle okuma anında
uygulandığı için burada ayrıca fiyat düzeltilmez.
"""
from __future__ import annotations

import logging
from datetime import date

from src.domain.ports.repositories.i_price_repo import IPriceRepository

logger = logging.getLogger(__name__)


def _validate(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")


class BackfillService:
    def __init__(self, stock_repo, price_repo: IPriceRepository, price_refresher) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._refresher = price_refresher

    def backfill_range(self, start_date: date, end_date: date) -> int:
        """Tüm takip edilen hisseler için aralığı indirir; SQLite'a yazılan satır sayısı."""
        _validate(start_date, end_date)
        stocks = [s for s in self._stock_repo.get_all_stocks() if s.id is not None]
        if not stocks:
            raise ValueError("Veritabanında kayıtlı hisse yok.")
        result = self._refresher.refresh(stocks, start_date, end_date)
        for error in result.errors:
            logger.warning("Backfill: %s", error)
        return result.updated_count

    def backfill_for_single_stock(self, stock_id: int, ticker: str, start_date: date, end_date: date) -> int:
        """Tek hisse için aralığı yeniden indirir (ör. sermaye artırımı sonrası); SQLite'a yazılan satır sayısı."""
        _validate(start_date, end_date)
        stock = self._stock_repo.get_stock_by_id(stock_id)
        if stock is None:
            raise ValueError(f"Hisse bulunamadı: {ticker} (id={stock_id})")
        return self._refresher.refresh([stock], start_date, end_date).updated_count

    def delete_range(self, start_date: date, end_date: date) -> int:
        """Aralıktaki fiyatları DuckDB'den (kaynak) ve SQLite'tan (yansıma) siler; silinen SQLite satırı."""
        _validate(start_date, end_date)
        stocks = [s for s in self._stock_repo.get_all_stocks() if s.id is not None]
        self._refresher.delete_range(stocks, start_date, end_date)
        return self._price_repo.delete_prices_in_range(start_date, end_date)
