"""
BistBulkDownloader — Tüm BIST hisselerinin ilk işlem gününden bugüne kadar olan
günlük OHLCV geçmişini TradingView ve YFinance üzerinden DuckDB'ye indiren servis.

Mimari:
- TradingView Scanner API ile aktif 600+ BIST hissesi listesi alınır.
- YFinance period='max' ile hissenin halka arzından günümüze kadar tüm günlük barları çekilir.
- DuckDB'ye (data/market_history.duckdb) sütunsal ve sıkıştırılmış olarak kaydedilir.
- Çoklu iş parçacığı (ThreadPoolExecutor) ve hata toleransı ile çalışır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import duckdb
import pandas as pd
import requests
import yfinance as yf

from src.infrastructure.db.paths import duckdb_path as default_duckdb_path
from src.infrastructure.retry import retry_call

logger = logging.getLogger(__name__)

_TV_SCANNER_URL = "https://scanner.tradingview.com/turkey/scan"
_DOWNLOAD_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 2.0


class BistBulkDownloader:
    """
    Tüm BIST hisselerinin eksiksiz zaman serisini indirip DuckDB'ye aktarır.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_workers: int = 4,
    ) -> None:
        self._db_path = str(db_path) if db_path else str(default_duckdb_path())
        self._max_workers = max_workers
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @property
    def db_path(self) -> str:
        return self._db_path

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self._db_path, read_only=False)

    def _init_db(self) -> None:
        with self._get_connection() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS bist_stocks (
                    ticker VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    currency_code VARCHAR DEFAULT 'TRY',
                    first_date DATE,
                    last_date DATE,
                    total_bars INTEGER,
                    updated_at TIMESTAMP
                );
            """)
            # Eski tablolarda updated_at olmayabilir, ekle
            con.execute("ALTER TABLE bist_stocks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;")

            con.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    ticker VARCHAR,
                    price_date DATE,
                    open_price DOUBLE,
                    high_price DOUBLE,
                    low_price DOUBLE,
                    close_price DOUBLE,
                    volume BIGINT,
                    PRIMARY KEY (ticker, price_date)
                );
            """)

    def fetch_all_bist_tickers(self) -> List[str]:
        """TradingView Scanner API'sinden tüm BIST hisse sembollerini çeker."""
        payload = {
            "filter": [],
            "options": {"lang": "tr"},
            "symbols": {"query": {"types": ["stock"]}},
            "sort": {"sortBy": "name", "sortOrder": "asc"},
            "range": [0, 1500],
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.post(_TV_SCANNER_URL, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                tickers = [
                    item["s"].split(":")[-1].strip().upper()
                    for item in data.get("data", [])
                    if "s" in item
                ]
                # Filtrele: sadece harf/rakam olan saf BIST kodları
                clean_tickers = sorted(list({t for t in tickers if t.isalnum() and len(t) <= 6}))
                logger.info("TradingView'den %d BIST hissesi tespit edildi.", len(clean_tickers))
                return clean_tickers
        except Exception as exc:
            logger.warning("TradingView scanner API hatası: %s", exc)

        # Fallback: Yerel DuckDB'deki mevcut ticker'lar
        with self._get_connection() as con:
            rows = con.execute("SELECT DISTINCT ticker FROM daily_prices").fetchall()
            return [r[0] for r in rows]

    def download_stock_history(self, ticker: str) -> Optional[pd.DataFrame]:
        """Tek bir hissenin tüm geçmişini (period='max') çeker."""
        clean = ticker.replace(".IS", "").strip().upper()
        yf_symbol = f"{clean}.IS"
        try:
            # yfinance bu çağrıda çoğu hatayı genel istisna olarak döndürür; her hata yeniden denenir.
            hist = retry_call(
                lambda: yf.Ticker(yf_symbol).history(period="max", auto_adjust=False),
                attempts=_DOWNLOAD_ATTEMPTS,
                base_delay=_RETRY_BACKOFF_SECONDS,
                is_retryable=lambda _exc: True,
                label=f"{clean} indirme",
            )
        except Exception as exc:
            logger.warning("%s indirilemedi: %s", clean, exc)
            return None
        if hist is None or hist.empty:
            return None
        return self.normalize_history_frame(clean, hist)

    @staticmethod
    def normalize_history_frame(clean_ticker: str, hist: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Yahoo geçmişini DuckDB şemasına çevirir; kapanışı NaN/<=0 olan (kısmi veya hayalet) barları eler."""
        try:
            hist = hist.reset_index()
            date_col = "Date" if "Date" in hist.columns else hist.columns[0]
            hist["price_date"] = pd.to_datetime(hist[date_col]).dt.date
            hist["ticker"] = clean_ticker
            hist["open_price"] = hist["Open"].astype(float)
            hist["high_price"] = hist["High"].astype(float)
            hist["low_price"] = hist["Low"].astype(float)
            hist["close_price"] = hist["Close"].astype(float)
            hist["volume"] = hist["Volume"].fillna(0).astype(int)
            valid = hist[hist["close_price"] > 0]  # NaN karşılaştırması False verir
            if valid.empty:
                return None
            return valid[["ticker", "price_date", "open_price", "high_price", "low_price", "close_price", "volume"]]
        except Exception as exc:
            logger.warning("%s geçmişi işlenemedi: %s", clean_ticker, exc)
            return None

    def save_stock_history(self, df: pd.DataFrame) -> int:
        """DataFrame'i DuckDB'ye topluca (bulk) yazar."""
        if df is None or df.empty:
            return 0

        ticker = df["ticker"].iloc[0]
        min_date = df["price_date"].min()
        max_date = df["price_date"].max()
        total_rows = len(df)

        with self._get_connection() as con:
            # DuckDB temp view üzerinden ultra hızlı bulk insert/replace
            con.register("temp_incoming", df)
            con.execute("""
                INSERT OR REPLACE INTO daily_prices
                SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                FROM temp_incoming
            """)
            con.execute("""
                INSERT OR REPLACE INTO bist_stocks (ticker, first_date, last_date, total_bars, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, [ticker, min_date, max_date, total_rows, datetime.now()])
            con.unregister("temp_incoming")

        return total_rows

    def sync_all(
        self,
        tickers: Optional[List[str]] = None,
        progress_cb: Optional[Callable[[int, int, str, int], None]] = None,
    ) -> Dict[str, int]:
        """
        Tüm veya seçilen BIST hisselerini paralel indirir.

        progress_cb: (completed_count, total_count, current_ticker, rows_saved)
        Dönüş: {ticker: saved_rows_count}
        """
        all_tickers = tickers or self.fetch_all_bist_tickers()
        total = len(all_tickers)
        results: Dict[str, int] = {}
        completed = 0

        logger.info("%d hisse için geçmiş veri indirme işlemi başlatılıyor...", total)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.download_stock_history, tk): tk
                for tk in all_tickers
            }

            for future in as_completed(future_to_ticker):
                tk = future_to_ticker[future]
                completed += 1
                rows = 0
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        rows = self.save_stock_history(df)
                        results[tk] = rows
                except Exception as exc:
                    logger.warning("%s kaydedilemedi: %s", tk, exc)

                if progress_cb:
                    progress_cb(completed, total, tk, rows)

        logger.info("Tarama ve senkronizasyon tamamlandı: %d hisse güncellendi.", len(results))
        return results
