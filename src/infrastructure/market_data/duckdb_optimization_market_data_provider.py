"""
DuckDBOptimizationMarketDataProvider — DuckDB tabanlı yüksek performanslı piyasa veri sağlayıcısı.

Sorumluluk:
- data/market_history.duckdb dosyasından BIST hisselerinin tarihsel kapanış fiyatlarını
  ve son fiyatlarını anında (milisaniyeler mertebesinde) çeker.
- DuckDB'de bulunmayan veya yetersiz verisi olan hisseler için opsiyonel fallback_provider
  (örn: YFinanceOptimizationMarketDataProvider) üzerinden sorgulama yapar.
- OptimizationMarketDataProvider protokolünü eksiksiz uygular.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import duckdb
import pandas as pd

from src.application.services.planning.optimization_market_data import OptimizationMarketDataProvider
from src.infrastructure.db.paths import duckdb_path as default_duckdb_path

logger = logging.getLogger(__name__)



class DuckDBOptimizationMarketDataProvider:
    """DuckDB üzerinden optimize edilmiş tarihsel fiyat ve son fiyat sağlayıcısı."""

    def __init__(
        self,
        duckdb_path: Optional[str] = None,
        fallback_provider: Optional[OptimizationMarketDataProvider] = None,
    ) -> None:
        self._duckdb_path = str(duckdb_path) if duckdb_path else str(default_duckdb_path())
        self._fallback_provider = fallback_provider

    def _get_connection(self) -> Optional[duckdb.DuckDBPyConnection]:
        if not Path(self._duckdb_path).exists():
            return None
        try:
            return duckdb.connect(self._duckdb_path, read_only=True)
        except Exception as exc:
            logger.warning("DuckDB bağlantısı açılamadı (%s): %s", self._duckdb_path, exc)
            return None

    def get_historical_prices(self, tickers: List[str], days: int = 504) -> pd.DataFrame:
        """Belirtilen hisselerin son `days` günlük düzeltilmiş kapanış fiyatlarını DataFrame olarak döner."""
        if not tickers:
            return pd.DataFrame()

        # Sembol eşlemeleri: 'THYAO.IS' -> 'THYAO'
        ticker_map = {t: t.replace(".IS", "").strip().upper() for t in tickers}
        reverse_map = {clean: orig for orig, clean in ticker_map.items()}
        clean_tickers = list(ticker_map.values())

        con = self._get_connection()
        if con is not None:
            try:
                query = """
                    SELECT price_date, ticker, close_price
                    FROM daily_prices
                    WHERE ticker = ANY(?) AND close_price > 0
                    ORDER BY price_date ASC
                """
                raw_df = con.execute(query, [clean_tickers]).df()
                if not raw_df.empty:
                    pivoted = raw_df.pivot(index="price_date", columns="ticker", values="close_price")
                    # Orijinal ticker sembol isimlerine geri eşle
                    pivoted = pivoted.rename(columns=reverse_map)

                    # En az 60 geçerli barı olan kolonları koru
                    valid_cols = [c for c in pivoted.columns if pivoted[c].notna().sum() >= 60]
                    if len(valid_cols) >= 2:
                        res_df = pivoted[valid_cols].tail(days).dropna()
                        if len(res_df) >= 60:
                            return res_df
            except Exception as exc:
                logger.warning("DuckDB tarihsel fiyat sorgulama hatası: %s", exc)
            finally:
                try:
                    con.close()
                except Exception:
                    pass

        # Fallback sağlayıcısına delege et
        if self._fallback_provider is not None:
            logger.info("DuckDB verisi yetersiz/bulunamadı; fallback sağlayıcı çağrılıyor...")
            return self._fallback_provider.get_historical_prices(tickers, days)

        return pd.DataFrame()

    def get_last_price(self, ticker: str) -> Optional[float]:
        """Belirtilen hissenin en son geçerli kapanış fiyatını döner."""
        clean = ticker.replace(".IS", "").strip().upper()

        con = self._get_connection()
        if con is not None:
            try:
                row = con.execute(
                    "SELECT close_price FROM daily_prices WHERE ticker = ? AND close_price > 0 ORDER BY price_date DESC LIMIT 1",
                    [clean],
                ).fetchone()
                if row and row[0] is not None:
                    return float(row[0])
            except Exception as exc:
                logger.debug("DuckDB son fiyat sorgu hatası (%s): %s", ticker, exc)
            finally:
                try:
                    con.close()
                except Exception:
                    pass

        if self._fallback_provider is not None:
            return self._fallback_provider.get_last_price(ticker)

        return None
