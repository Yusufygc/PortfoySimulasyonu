"""Tek fiyat kaynağına geçiş (bir kez): SQLite'taki doğru düzeltmeleri DuckDB'ye aktar, sonra yansıt.

SQLite eskiden kendi kurumsal aksiyon düzeltmelerini tutuyordu. Bir hissenin SQLite geçmişi DuckDB'de henüz
onaylanmamış bir faktörle düzeltilmişse (ör. RUZYE: 2019 öncesi ~0,76), doğrudan yansıtma bu düzeltmeyi geri
alırdı. Geçiş önce bu hisseler için `MarketCorporateActionService.import_actions_from_adjusted_history` ile faktörü
DuckDB'ye ONAYLI olay olarak kaydeder (ham seri kırılmayı gösteriyorsa), sonra tüm hisseleri yansıtır.
Tamamlandığında `app_settings` bayrağı yazılır; sonraki çağrılar hiçbir şey yapmaz.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, NamedTuple

from src.domain.market_clock import market_today

logger = logging.getLogger(__name__)

DONE_SETTING = "prices.single_source_migrated"
DEVIATION = 0.005       # %0,5'ten büyük fark sapma sayılır
WIDESPREAD = 0.10       # satırların bu oranından fazlası sapıyorsa yaygın
FACTOR_TRACE = 0.05     # oran medyanı 1'den bu kadar uzaksa sapma bir faktör izidir (temettü karışımı değil)
EARLIEST = date(2000, 1, 1)


@dataclass
class MigrationReport:
    factor_stocks: List[str] = field(default_factory=list)      # faktör izi taşıyan hisseler
    imported_actions: Dict[str, int] = field(default_factory=dict)
    unresolved: List[str] = field(default_factory=list)          # faktör ham seride doğrulanamadı: DuckDB esas
    projected_rows: int = 0
    skipped: bool = False


def factor_trace(stored: Dict[date, float], reference: Dict[date, float]) -> float | None:
    """SQLite/DuckDB oran medyanı; sapma yaygın ve faktör büyüklüğündeyse oran, değilse None."""
    ratios = sorted(stored[d] / reference[d] for d in stored if reference.get(d, 0) > 0 and stored[d] > 0)
    if not ratios:
        return None
    deviating = [r for r in ratios if abs(r - 1.0) > DEVIATION]
    if len(deviating) / len(ratios) <= WIDESPREAD:
        return None
    median = deviating[len(deviating) // 2]
    return median if abs(median - 1.0) > FACTOR_TRACE else None


class MigrationDeps(NamedTuple):
    stock_repo: object
    price_repo: object
    history_repo: object            # DuckDB okuyucu (düzeltilmiş seri)
    market_action_service: object   # faktör içe aktarma
    projection: object              # PriceProjectionService
    settings_repo: object = None    # tamamlandı bayrağı


class SinglePriceSourceMigration:
    def __init__(self, deps: MigrationDeps) -> None:
        self._stocks = deps.stock_repo
        self._prices = deps.price_repo
        self._history = deps.history_repo
        self._market = deps.market_action_service
        self._projection = deps.projection
        self._settings = deps.settings_repo

    def is_done(self) -> bool:
        return self._settings is not None and (self._settings.get(DONE_SETTING) or "") == "1"

    def run_once(self) -> MigrationReport:
        if self.is_done():
            return MigrationReport(skipped=True)
        report = self.run()
        if self._settings is not None:
            self._settings.set(DONE_SETTING, "1")
        return report

    def run(self) -> MigrationReport:
        """Bayrağa bakmadan geçişi çalıştırır (betik ve testler için)."""
        report = MigrationReport()
        stocks = [s for s in self._stocks.get_all_stocks() if s.id is not None]
        for stock in stocks:
            self._import_factor_if_needed(stock, report)
        report.projected_rows = self._projection.project().written_count
        logger.info("Tek fiyat kaynağı geçişi: %d hissede faktör izi, %d olay içe aktarıldı, %d satır yansıtıldı",
                    len(report.factor_stocks), sum(report.imported_actions.values()), report.projected_rows)
        return report

    def _import_factor_if_needed(self, stock, report: MigrationReport) -> None:
        ticker = (stock.ticker or "").strip().upper().replace(".IS", "")
        stored = {p.price_date: float(p.close_price) for p in self._prices.get_price_series(stock.id, EARLIEST, market_today())}
        if not stored:
            return
        reference = {b.price_date: b.close_price for b in self._history.get_price_series(ticker, min(stored), max(stored))}
        if factor_trace(stored, reference) is None:
            return
        report.factor_stocks.append(ticker)
        created = self._market.import_actions_from_adjusted_history(ticker, stored)
        report.imported_actions[ticker] = len(created)
        if not created:
            # ham seride kırılma yok: SQLite'taki düzeltme kaynakta doğrulanamıyor (çoğu zaman eski temettü-düzeltmeli
            # indirme); politika gereği DuckDB (ham + onaylı faktör) esas alınır
            report.unresolved.append(ticker)
            logger.warning("%s: SQLite düzeltmesi DuckDB ham serisinde doğrulanamadı; DuckDB değerleri esas alınacak", ticker)

