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
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Set

import duckdb
import pandas as pd
import yfinance as yf

from src.application.services.market.trading_calendar import MarketTradingCalendar, WeekdayTradingCalendar
from src.domain.models.daily_price import DailyPrice
from src.infrastructure.db.paths import duckdb_path as default_duckdb_path
from src.domain.market_clock import market_now

logger = logging.getLogger(__name__)

_MARKET_CLOSE_TIME = dt_time(18, 15)  # BIST seans kapanışı + marj kesinleşme saati


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
        duckdb_path: Optional[str] = None,
        trading_calendar: Optional[MarketTradingCalendar] = None,
        max_workers: int = 6,
        price_repo=None,
        stock_repo=None,
        market_action_service=None,
        portfolio_action_repo=None,
    ) -> None:
        """
        price_repo / stock_repo: SQLite (OLTP) tarafı. Verilirse, portföyde kayıtlı hisselerin yeni
        kapanışları SQLite `daily_prices` tablosuna da yazılır; verilmezse yalnızca DuckDB güncellenir.
        market_action_service / portfolio_action_repo: verilirse her senkronda portföy kurumsal aksiyonları
        DuckDB'ye aktarılır ve onaylı olayların ham veride hâlâ kırılma gösterdiği doğrulanır.
        """
        self._duckdb_path = str(duckdb_path) if duckdb_path else str(default_duckdb_path())
        self._trading_calendar = trading_calendar or WeekdayTradingCalendar()
        self._max_workers = max_workers
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._market_action_service = market_action_service
        self._portfolio_action_repo = portfolio_action_repo

    def refresh_corporate_actions(self) -> None:
        """Portföy aksiyonlarını DuckDB'ye aktarır, onaylı olayları ham veriye karşı doğrular (hata sync'i bozmaz)."""
        if self._market_action_service is None or not Path(self._duckdb_path).exists():
            return
        try:
            if self._portfolio_action_repo is not None and self._stock_repo is not None:
                self._market_action_service.import_portfolio_actions(self._portfolio_action_repo, self._stock_repo)
            self._market_action_service.verify_actions()
        except Exception as exc:
            logger.warning("Kurumsal aksiyon yenilemesi başarısız: %s", exc)

    def _get_duckdb_conn(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        Path(self._duckdb_path).parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(self._duckdb_path, read_only=read_only)

    def get_last_completed_trading_day(self, now: Optional[datetime] = None) -> date:
        """
        BIST'in son tamamlanmış (kapanmış) işlem gününü hesaplar.
        Hafta içi saat 18:15'ten önce ise dünü; hafta sonu ise Cuma gününü verir.
        """
        current_dt = now or market_now()
        current_date = current_dt.date()
        current_time = current_dt.time()

        # Bugün işlem günü mü ve seans bitti mi?
        if self._trading_calendar.is_trading_day(current_date):
            if current_time >= _MARKET_CLOSE_TIME:
                return current_date

        # Değilse geriye doğru en son açık işlem gününü bul
        candidate = current_date - timedelta(days=1)
        while not self._trading_calendar.is_trading_day(candidate):
            candidate -= timedelta(days=1)
        return candidate

    def get_sync_status(self, now: Optional[datetime] = None) -> MarketSyncStatus:
        """
        DuckDB'deki en son veri tarihi ile piyasa durumunu karşılaştırır.
        """
        last_trading_day = self.get_last_completed_trading_day(now)

        max_db_date = None
        if Path(self._duckdb_path).exists():
            try:
                with self._get_duckdb_conn(read_only=True) as con:
                    res = con.execute("SELECT MAX(last_date) FROM bist_stocks").fetchone()
                    if res and res[0]:
                        max_db_date = res[0]
                        if isinstance(max_db_date, datetime):
                            max_db_date = max_db_date.date()
            except Exception as exc:
                logger.warning("DuckDB max_date okunamadı: %s", exc)

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
        if not Path(self._duckdb_path).exists():
            return None
        try:
            with self._get_duckdb_conn(read_only=True) as con:
                row = con.execute(
                    "SELECT MIN(price_date) FROM daily_prices "
                    "WHERE (close_price IS NULL OR close_price <= 0) AND price_date >= ? AND price_date <= ?",
                    [last_trading_day - timedelta(days=30), last_trading_day],
                ).fetchone()
        except Exception as exc:
            logger.debug("Geçersiz bar taraması başarısız: %s", exc)
            return None
        found = row[0] if row else None
        return found.date() if isinstance(found, datetime) else found

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

        # Hedef hisseler
        with self._get_duckdb_conn(read_only=True) as con:
            tickers = [r[0] for r in con.execute("SELECT ticker FROM bist_stocks ORDER BY ticker").fetchall()]

        if not tickers:
            return MarketSyncResult(
                is_up_to_date=False,
                updated_stocks=0,
                added_bars=0,
                elapsed_seconds=round(time.time() - t0, 2),
                message="DuckDB'de hisse listesi bulunamadı.",
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

        # Batch indirme (50'şerli parçalarla YFinance batch download)
        chunk_size = 50
        total_added_bars = 0
        updated_stocks = 0
        errors: List[str] = []

        all_collected_dfs: List[pd.DataFrame] = []

        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i : i + chunk_size]
            symbols_str = " ".join([f"{tk}.IS" for tk in chunk])
            try:
                data = yf.download(
                    symbols_str,
                    start=start_date.isoformat(),
                    end=end_date.isoformat(),
                    group_by="ticker",
                    auto_adjust=False,
                    threads=True,
                    progress=False,
                )
                if data is None or data.empty:
                    continue

                for tk in chunk:
                    clean_tk = tk
                    yf_sym = f"{tk}.IS"
                    try:
                        # Tekli mi çoklu mu kontrol et
                        if len(chunk) == 1:
                            df_sub = data.copy()
                        elif yf_sym in data.columns.levels[0]:
                            df_sub = data[yf_sym].dropna(how="all").copy()
                        else:
                            continue

                        if df_sub.empty:
                            continue

                        df_sub = df_sub.reset_index()
                        date_col = "Date" if "Date" in df_sub.columns else df_sub.columns[0]
                        df_sub["price_date"] = pd.to_datetime(df_sub[date_col]).dt.date
                        df_sub["ticker"] = clean_tk
                        df_sub["open_price"] = df_sub["Open"].astype(float)
                        df_sub["high_price"] = df_sub["High"].astype(float)
                        df_sub["low_price"] = df_sub["Low"].astype(float)
                        df_sub["close_price"] = df_sub["Close"].astype(float)
                        df_sub["volume"] = df_sub["Volume"].fillna(0).astype(int)

                        # Geçerli kapanış fiyatı olan satırları filtrele
                        valid = df_sub[df_sub["close_price"] > 0]
                        if not valid.empty:
                            all_collected_dfs.append(valid[["ticker", "price_date", "open_price", "high_price", "low_price", "close_price", "volume"]])
                            updated_stocks += 1
                    except Exception as sub_err:
                        logger.debug("Hisse parse hatası (%s): %s", tk, sub_err)

            except Exception as batch_err:
                msg = f"Batch indirme hatası (blok {i}): {batch_err}"
                logger.warning(msg)
                errors.append(msg)

        # DuckDB'ye tek hamlede bulk insert
        if all_collected_dfs:
            combined = pd.concat(all_collected_dfs, ignore_index=True)
            total_added_bars = len(combined)

            with self._get_duckdb_conn(read_only=False) as con:
                con.register("temp_delta", combined)
                con.execute("""
                    INSERT OR REPLACE INTO daily_prices
                    SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                    FROM temp_delta
                """)
                # Yeniden indirilemeyen (kısmi/hayalet) geçersiz kapanışlı barlar yeni veriyle değiştirildi; kalanlar atılır
                con.execute("DELETE FROM daily_prices WHERE close_price IS NULL OR close_price <= 0")
                con.execute("""
                    UPDATE bist_stocks
                    SET last_date = sub.max_d,
                        total_bars = sub.cnt,
                        updated_at = ?
                    FROM (
                        SELECT ticker, MAX(price_date) as max_d, COUNT(*) as cnt
                        FROM daily_prices
                        GROUP BY ticker
                    ) sub
                    WHERE bist_stocks.ticker = sub.ticker
                """, [datetime.now()])
                con.unregister("temp_delta")

            # SQLite portföy hisseleri için köprü güncelleme
            self._sync_to_sqlite(combined)

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
        """DuckDB'de bulunup SQLite `daily_prices`'ta olmayan YENİ barları portföy hisseleri için SQLite'a taşır.

        Her hisse için yalnızca SQLite'taki son kapanış tarihinden sonraki barlar alınır; mevcut
        (örneğin sermaye artırımıyla düzeltilmiş) geçmiş barlar asla üzerine yazılmaz.
        Döndürür: yazılan bar sayısı.
        """
        if self._price_repo is None or self._stock_repo is None or not Path(self._duckdb_path).exists():
            return 0
        try:
            stocks = [s for s in self._stock_repo.get_all_stocks() if s.id is not None]
            if not stocks:
                return 0
            ticker_by_id = {s.id: (s.ticker or "").replace(".IS", "").strip().upper() for s in stocks}
            last_dates = self._price_repo.get_latest_price_dates(list(ticker_by_id))
            floor = min((last_dates.get(sid) for sid in ticker_by_id if last_dates.get(sid)), default=None)
            tickers = sorted(set(ticker_by_id.values()))
            with self._get_duckdb_conn(read_only=True) as con:
                frame = con.execute(
                    "SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume "
                    "FROM daily_prices WHERE close_price > 0 AND price_date > ? AND ticker IN (SELECT UNNEST(?))",
                    [floor or date(2000, 1, 1), tickers],
                ).fetchdf()
            if frame.empty:
                return 0
            frame["price_date"] = pd.to_datetime(frame["price_date"]).dt.date
            last_by_ticker = {
                ticker_by_id[sid]: last_dates[sid] for sid in ticker_by_id if last_dates.get(sid)
            }
            keep = [
                row.price_date > last_by_ticker.get(row.ticker, date(2000, 1, 1))
                for row in frame.itertuples(index=False)
            ]
            frame = frame[keep]
            if frame.empty:
                return 0
            return self._sync_to_sqlite(frame)
        except Exception as exc:
            logger.warning("SQLite uzlaştırması başarısız: %s", exc)
            return 0

    def _sync_to_sqlite(self, df_bars: pd.DataFrame) -> int:
        """SQLite'ta kayıtlı portföy hisselerine de yeni kapanışları repository üzerinden yazar.

        Döndürür: yazılan bar sayısı. Hata, DuckDB güncellemesini bozmaz (yalnızca loglanır).
        """
        if self._price_repo is None or self._stock_repo is None or df_bars.empty:
            return 0
        try:
            stock_ids = {
                (stock.ticker or "").replace(".IS", "").strip().upper(): stock.id
                for stock in self._stock_repo.get_all_stocks()
                if stock.id is not None
            }
            prices: List[DailyPrice] = []
            for row in df_bars.itertuples(index=False):
                stock_id = stock_ids.get(row.ticker)
                if stock_id is None or not row.close_price or row.close_price <= 0:
                    continue
                prices.append(DailyPrice(
                    id=None,
                    stock_id=stock_id,
                    price_date=row.price_date,
                    close_price=Decimal(str(row.close_price)),
                    currency_code="TRY",
                    source="market_sync",
                    open_price=Decimal(str(row.open_price)) if row.open_price == row.open_price else None,
                    high_price=Decimal(str(row.high_price)) if row.high_price == row.high_price else None,
                    low_price=Decimal(str(row.low_price)) if row.low_price == row.low_price else None,
                    volume=int(row.volume) if row.volume == row.volume else None,
                ))
            if prices:
                self._price_repo.upsert_daily_prices_bulk(prices)
                logger.info("SQLite senkronizasyonu: %d satır güncellendi.", len(prices))
            return len(prices)
        except Exception as exc:
            logger.warning("SQLite senkronizasyon köprüsü hatası: %s", exc)
            return 0
