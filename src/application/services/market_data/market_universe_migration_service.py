"""SQLite'taki piyasa fiyat geçmişini DuckDB tek evrenine taşıma (bir kerelik göç).

Hedef: piyasa verisinin sahibi DuckDB olur; SQLite yalnızca kullanıcı verisine (işlem, izleme listesi, model
portföy, kurumsal aksiyon) bağlı hisselerin fiyatlarını tutar. Kullanıcı verisine bağlı olmayan hisselerin
SQLite fiyat geçmişi ve kayıtları silinir. Silmeden önce:
1. DuckDB'nin hisseyi kapsadığı doğrulanır (kapsamayan hisse silinmez),
2. SQLite'taki DÜZELTİLMİŞ geçmiş ile DuckDB ham geçmişinin farkından geçmiş sermaye artırımları türetilip DuckDB'ye
   ONAYLI olay olarak yazılır (düzeltme bilgisi kaybolmaz).
Yedekleme ve çalıştırma `scripts/migrate_market_universe_to_duckdb.py` içindedir.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import List
from src.domain.market_clock import market_today

logger = logging.getLogger(__name__)

_EARLIEST = date(1990, 1, 1)


@dataclass
class MigrationEntry:
    stock_id: int
    ticker: str
    sqlite_bars: int
    duckdb_bars: int
    referenced: bool
    covered_by_duckdb: bool


@dataclass
class MigrationPlan:
    entries: List[MigrationEntry] = field(default_factory=list)

    @property
    def deletable(self) -> List[MigrationEntry]:
        return [e for e in self.entries if not e.referenced and e.covered_by_duckdb]

    @property
    def kept_referenced(self) -> List[MigrationEntry]:
        return [e for e in self.entries if e.referenced]

    @property
    def kept_uncovered(self) -> List[MigrationEntry]:
        return [e for e in self.entries if not e.referenced and not e.covered_by_duckdb]


@dataclass
class MigrationResult:
    derived_actions: int = 0
    deleted_prices: int = 0
    deleted_stocks: int = 0
    errors: List[str] = field(default_factory=list)


class MarketUniverseMigrationService:
    def __init__(self, stock_repo, price_repo, maintenance_repo, market_history_repo, market_action_service) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._maintenance = maintenance_repo
        self._history = market_history_repo
        self._actions = market_action_service

    def plan(self) -> MigrationPlan:
        unreferenced = set(self._maintenance.unreferenced_stock_ids())
        today = market_today()
        plan = MigrationPlan()
        for stock in self._stock_repo.get_all_stocks():
            if stock.id is None:
                continue
            sqlite_rows = self._price_repo.get_price_series(stock.id, _EARLIEST, today)
            duck_bars = self._history.get_price_series(stock.ticker, _EARLIEST, today, adjusted=False)
            plan.entries.append(MigrationEntry(
                stock_id=stock.id,
                ticker=stock.ticker,
                sqlite_bars=len(sqlite_rows),
                duckdb_bars=len(duck_bars),
                referenced=stock.id not in unreferenced,
                covered_by_duckdb=self._is_covered(sqlite_rows, duck_bars),
            ))
        return plan

    @staticmethod
    def _is_covered(sqlite_rows, duck_bars) -> bool:
        """SQLite verisi kaybolmaz: DuckDB aynı başlangıçtan itibaren en az %90 bar sayısına sahip olmalı."""
        if not sqlite_rows:
            return True
        if not duck_bars:
            return False
        first_sqlite = min(r.price_date for r in sqlite_rows)
        starts_early_enough = (duck_bars[0].price_date - first_sqlite).days <= 7
        return starts_early_enough and len(duck_bars) >= 0.9 * len(sqlite_rows)

    def execute(self, plan: MigrationPlan) -> MigrationResult:
        result = MigrationResult()
        today = market_today()
        # 1) Düzeltme bilgisini DuckDB'ye taşı (kullanıcı verisine bağlı hisseler dahil: onların SQLite fiyatları kalır
        #    ama DuckDB tarafı da aynı bazı görmeli)
        for entry in plan.entries:
            if entry.sqlite_bars == 0 or entry.duckdb_bars == 0:
                continue
            try:
                rows = self._price_repo.get_price_series(entry.stock_id, _EARLIEST, today)
                adjusted = {r.price_date: float(r.close_price) for r in rows if r.close_price and r.close_price > 0}
                result.derived_actions += len(self._actions.import_actions_from_adjusted_history(entry.ticker, adjusted))
            except Exception as exc:
                result.errors.append(f"{entry.ticker}: {exc}")
                logger.warning("Düzeltme türetilemedi (%s): %s", entry.ticker, exc)
        # 2) Referanssız ve DuckDB'nin kapsadığı hisseleri sil
        deletable_ids = [e.stock_id for e in plan.deletable]
        if deletable_ids:
            result.deleted_prices, result.deleted_stocks = self._maintenance.delete_unreferenced_stocks(deletable_ids)
        return result
