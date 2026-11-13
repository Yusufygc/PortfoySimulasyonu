"""
MarketDataSyncService — İşlem günlerinde piyasa kapanışlarında veya son güncel gün
ile aktif gün arasındaki eksik verileri otomatik güncelleyen profesyonel servis.

Sorumluluklar:
1. Akıllı Gap Tespiti: DuckDB'deki MAX(last_date) ile BIST takvimindeki son kapanmış işlem gününü kıyaslar.
2. Artımlı Senkronizasyon (Incremental Sync): Sadece eksik günleri (delta) indirir (tüm tarihi tekrar indirmez).
3. Çift Katman Güncelleme: DuckDB'yi (ve SQLite'ta kayıtlı portföy hisselerini, repository'ler üzerinden) günceller.
4. Ağ Optimizasyonu: Batch ve thread-pool kullanarak 600+ hisseyi 2-4 saniyede günceller.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Sequence

from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.application.services.market.trading_calendar import MarketTradingCalendar, WeekdayTradingCalendar
from src.domain.market_clock import market_now
from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_market_history_store import IMarketBarDownloader, IMarketHistoryStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketSyncStatus:
    max_db_date: Optional[date]
    last_completed_trading_day: date
    is_up_to_date: bool
    missing_trading_days: List[date]
    message: str


@dataclass(frozen=True)
class MarketSyncResult:
    is_up_to_date: bool
    updated_stocks: int
    added_bars: int
    elapsed_seconds: float
    message: str
    errors: List[str] = field(default_factory=list)


class MarketDataSyncService:
    """
    Piyasa kapanışlarında ve uygulama açılışında artımlı (incremental) veri senkronizasyonu yapar.
    """

    def __init__(
        self,
        store: IMarketHistoryStore,
        downloader: Optional[IMarketBarDownloader] = None,
        trading_calendar: Optional[MarketTradingCalendar] = None,
        **repos,
    ) -> None:
        """
        store: DuckDB piyasa geçmişi (yazma portu); downloader: dış kaynaktan bar indirme (yoksa indirme yapılmaz).
        `repos` (hepsi isteğe bağlı): `projection` (PriceProjectionService) ve `stock_repo` verilirse takip edilen
        hisselerin SQLite `daily_prices` yansıması güncellenir; `market_action_service` / `portfolio_action_repo`
        verilirse her senkronda portföy kurumsal aksiyonları DuckDB'ye aktarılır ve onaylı olaylar doğrulanır.
        """
        self._store = store
        self._downloader = downloader
        self._trading_calendar = trading_calendar or WeekdayTradingCalendar()
        self._session = BistMarketSessionService(trading_calendar=self._trading_calendar)
        self._price_repo = repos.pop("price_repo", None)
        self._stock_repo = repos.pop("stock_repo", None)
        self._projection = repos.pop("projection", None)  # PriceProjectionService: SQLite fiyat yansıması
        self._migration = repos.pop("migration", None)  # SinglePriceSourceMigration: ilk yansıtmadan önce bir kez
        self._market_action_service = repos.pop("market_action_service", None)
        self._portfolio_action_repo = repos.pop("portfolio_action_repo", None)
        if repos:
            raise TypeError(f"Bilinmeyen bağımlılık: {', '.join(sorted(repos))}")

    @property
    def store(self) -> IMarketHistoryStore:
        return self._store

    def refresh_corporate_actions(self) -> None:
        """Portföy aksiyonlarını DuckDB'ye aktarır, onaylı olayları ham veriye karşı doğrular (hata sync'i bozmaz)."""
        if self._market_action_service is None or not self._store.exists():
            return
        try:
            if self._portfolio_action_repo is not None and self._stock_repo is not None:
                self._market_action_service.import_portfolio_actions(self._portfolio_action_repo, self._stock_repo)
            self._market_action_service.verify_actions()
        except Exception as exc:
            logger.warning("Kurumsal aksiyon yenilemesi başarısız: %s", exc)

    def get_last_completed_trading_day(self, now: Optional[datetime] = None) -> date:
        """
        BIST'in kapanış verisi kesinleşmiş son işlem günü (Istanbul saati).
        Kapanış seansı (18:10, yarım gün 13:00) + veri gecikmesi (20 dk) geçmeden bugün sayılmaz;
        erken çekilen bar kapanış fiyatı değildir ve sonradan "güncel" sayılıp düzeltilmezdi.
        """
        return self._session.last_completed_trading_day(now or market_now())

    def get_sync_status(self, now: Optional[datetime] = None) -> MarketSyncStatus:
        """
        DuckDB'deki en son veri tarihi ile piyasa durumunu karşılaştırır.
        """
        last_trading_day = self.get_last_completed_trading_day(now)

        max_db_date = self._store.last_bar_date()

        if max_db_date is None:
            return MarketSyncStatus(
                max_db_date=None,
                last_completed_trading_day=last_trading_day,
                is_up_to_date=False,
                missing_trading_days=[last_trading_day],
                message="Veritabanında hiç borsa verisi bulunmuyor.",
            )

        # Eksik günleri tespit et
        missing_days: List[date] = []
        cur = max_db_date + timedelta(days=1)
        while cur <= last_trading_day:
            if self._trading_calendar.is_trading_day(cur):
                missing_days.append(cur)
            cur += timedelta(days=1)

        is_up_to_date = len(missing_days) == 0
        if is_up_to_date:
            msg = f"Tüm borsa verileri güncel (Son Kapanış: {max_db_date:%d.%m.%Y})."
        else:
            msg = f"{len(missing_days)} günlük borsa kapanış verisi eksik ({missing_days[0]:%d.%m.%Y} -> {missing_days[-1]:%d.%m.%Y})."

        return MarketSyncStatus(
            max_db_date=max_db_date,
            last_completed_trading_day=last_trading_day,
            is_up_to_date=is_up_to_date,
            missing_trading_days=missing_days,
            message=msg,
        )

    def _find_invalid_bar_start(self, last_trading_day: date) -> Optional[date]:
        """Son 30 günde kapanışı NULL/<=0 olan en eski bar tarihi (kısmi indirilmiş gün); yoksa None."""
        oldest, count, sample = self._store.invalid_bars(last_trading_day - timedelta(days=30), last_trading_day)
        if sample:
            # Tanı: her açılışta yeniden indirme tekrar ederse geçersiz barı yazan kaynağı bulmak için
            logger.warning(
                "Geçersiz kapanışlı %d bar bulundu (ilk 10: %s).",
                count, ", ".join(f"{ticker} {day}" for ticker, day in sample),
            )
        return oldest

    def sync_daily_delta(
        self,
        now: Optional[datetime] = None,
        force: bool = False,
    ) -> MarketSyncResult:
        """
        Sadece son kayıtlı gün ile son kapanmış gün arasındaki eksik verileri indirir.
        """
        t0 = time.time()
        # DuckDB'de olup SQLite'a yazılamamış barlar (eski köprü hatası vb.) önce kapatılır
        reconciled_bars = self.reconcile_sqlite_from_duckdb()
        self.refresh_corporate_actions()
        status = self.get_sync_status(now)
        repair_start = self._find_invalid_bar_start(status.last_completed_trading_day)

        if status.is_up_to_date and not force and repair_start is None:
            logger.info("MarketDataSyncService: %s", status.message)
            return MarketSyncResult(
                is_up_to_date=True,
                updated_stocks=0,
                added_bars=reconciled_bars,
                elapsed_seconds=round(time.time() - t0, 2),
                message=status.message,
            )

        tickers = self._store.list_tickers()
        if not tickers or self._downloader is None:
            return MarketSyncResult(
                is_up_to_date=False,
                updated_stocks=0,
                added_bars=0,
                elapsed_seconds=round(time.time() - t0, 2),
                message="DuckDB'de hisse listesi bulunamadı." if not tickers else "Piyasa verisi indiricisi yok.",
            )

        start_date = status.missing_trading_days[0] if status.missing_trading_days else (status.max_db_date or date.today())
        if repair_start is not None:
            start_date = min(start_date, repair_start)
            logger.info("MarketDataSyncService: geçersiz kapanışlı barlar %s tarihinden itibaren yeniden indirilecek.", repair_start)
        end_date = status.last_completed_trading_day + timedelta(days=1)  # yfinance end_date exclusive

        logger.info(
            "MarketDataSyncService: %d hisse için %s - %s aralığı artımlı indiriliyor...",
            len(tickers),
            start_date,
            status.last_completed_trading_day,
        )
        bars, updated_stocks, errors = self._downloader.download_daily(tickers, start_date, end_date)
        total_added_bars = len(bars)
        if bars:
            self._store.write_bars(bars)  # DuckDB'ye tek hamlede toplu yazım
            self._sync_to_sqlite(bars)  # SQLite portföy hisseleri için köprü güncelleme

        elapsed = round(time.time() - t0, 2)
        success_msg = f"Güncelleme tamamlandı: {updated_stocks} hisse için {total_added_bars:,} yeni bar eklendi ({elapsed} sn)."
        logger.info(success_msg)

        return MarketSyncResult(
            is_up_to_date=True,
            updated_stocks=updated_stocks,
            added_bars=total_added_bars,
            elapsed_seconds=elapsed,
            message=success_msg,
            errors=errors,
        )

    def reconcile_sqlite_from_duckdb(self) -> int:
        """Takip edilen hisselerin SQLite fiyatlarını DuckDB'den (ham + onaylı faktör) yeniden yansıtır.

        DuckDB fiyatın tek sahibidir; SQLite yansımadır (`PriceProjectionService`). Onaylanan/geri alınan kurumsal
        aksiyonlar ve hayalet bar temizliği böylece her senkronda SQLite'a da yansır. Döndürür: yazılan satır sayısı.
        """
        if self._projection is None or not self._store.exists():
            return 0
        try:
            if self._migration is not None and not self._migration.is_done():
                return self._migration.run_once().projected_rows  # faktörleri aktarır ve tam yansıtır
            return self._projection.project().written_count
        except Exception as exc:
            logger.warning("SQLite fiyat yansıtması başarısız: %s", exc)
            return 0

    def _sync_to_sqlite(self, bars: Sequence[MarketBar]) -> int:
        """Yeni DuckDB barlarının SQLite yansımasını günceller (yalnızca `stocks` tablosundaki hisseler).

        Döndürür: yazılan satır sayısı. Hata, DuckDB güncellemesini bozmaz (yalnızca loglanır).
        """
        if self._projection is None or self._stock_repo is None or not bars:
            return 0
        try:
            tickers = {bar.ticker for bar in bars}
            stock_ids = [
                stock.id for stock in self._stock_repo.get_all_stocks()
                if stock.id is not None and (stock.ticker or "").replace(".IS", "").strip().upper() in tickers
            ]
            if not stock_ids:
                return 0
            start, end = min(b.price_date for b in bars), max(b.price_date for b in bars)
            return self._projection.project(stock_ids, start, end).written_count
        except Exception as exc:
            logger.warning("SQLite fiyat yansıtması başarısız: %s", exc)
            return 0
