"""
DatabaseMaintenanceService — Ayarlar ekranı için veritabanı dosyası istatistikleri, bütünlük kontrolü ve
SQLite yedek dışa aktarımı.

SQLite (OLTP) ve DuckDB (OLAP) dosyalarını salt okunur açar. Arayüz katmanı ham bağlantı kullanmaz; yalnızca
bu servisin döndürdüğü sözlükleri ve metinleri gösterir.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb

from src.infrastructure.db.paths import duckdb_path, sqlite_db_path

logger = logging.getLogger(__name__)

_SQLITE_TABLES = [
    ("Hisse Senetleri (Katalog)", "stocks"),
    ("Gerçekleşen İşlemler (Emirler)", "trades"),
    ("Nakit Hareketleri & Sermaye", "cash_movements"),
    ("İzleme Listeleri (Watchlist)", "watchlists"),
    ("Model Portföyler (Simülasyon)", "model_portfolios"),
    ("Finansal Hedefler (Planning)", "financial_goals"),
]
_BACKUP_TABLES = ("stocks", "trades", "cash_movements", "watchlists")


def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    if size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    return f"{size_in_bytes / (1024 * 1024):.2f} MB"


def _thousands(value: int) -> str:
    return f"{value:,}".replace(",", ".")


class DatabaseMaintenanceService:
    def __init__(self, sqlite_path: Path, duckdb_file: Path) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.duckdb_path = Path(duckdb_file)

    @classmethod
    def from_config(cls, configured_sqlite_path: Optional[str] = None) -> "DatabaseMaintenanceService":
        sqlite_file = sqlite_db_path(configured_sqlite_path)
        return cls(sqlite_file, duckdb_path(sqlite_file))

    # ---- istatistik ---------------------------------------------------------------------
    def collect_stats(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        payload.update(self._sqlite_stats())
        payload.update(self._duckdb_stats())
        return payload

    def _sqlite_stats(self) -> Dict[str, Any]:
        try:
            if not self.sqlite_path.exists():
                return {"sqlite_size": "0 B (Dosya Yok)", "sqlite_table_stats": []}
            size = format_file_size(self.sqlite_path.stat().st_size)
            conn = sqlite3.connect(str(self.sqlite_path), timeout=5)
            try:
                stats = []
                for label, table in _SQLITE_TABLES:
                    try:
                        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        stats.append({"name": label, "count": _thousands(count)})
                    except Exception:
                        stats.append({"name": label, "count": "0"})
            finally:
                conn.close()
            return {"sqlite_size": size, "sqlite_table_stats": stats}
        except Exception as exc:
            logger.warning("SQLite istatistik hatası: %s", exc)
            return {"sqlite_size": "Hata", "sqlite_table_stats": []}

    def _duckdb_stats(self) -> Dict[str, Any]:
        empty = {"duckdb_stock_count": 0, "duckdb_total_bars": "0", "duckdb_last_date": "-", "duckdb_is_up_to_date": False}
        try:
            if not self.duckdb_path.exists():
                return {"duckdb_size": "0 B (Dosya Yok)", **empty}
            size = format_file_size(self.duckdb_path.stat().st_size)
            conn = duckdb.connect(str(self.duckdb_path), read_only=True)
            try:
                stock_count = conn.execute("SELECT COUNT(*) FROM bist_stocks").fetchone()[0]
                total_bars = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
                max_date = conn.execute("SELECT MAX(price_date) FROM daily_prices").fetchone()[0]
            finally:
                conn.close()
            if max_date:
                last_date = max_date.strftime("%d.%m.%Y") if hasattr(max_date, "strftime") else str(max_date)
            else:
                last_date = "-"
            return {
                "duckdb_size": size,
                "duckdb_stock_count": int(stock_count),
                "duckdb_total_bars": _thousands(int(total_bars)),
                "duckdb_last_date": last_date,
                "duckdb_is_up_to_date": True,
            }
        except Exception as exc:
            logger.warning("DuckDB istatistik hatası: %s", exc)
            return {"duckdb_size": "Hata", **empty}

    # ---- bütünlük -----------------------------------------------------------------------
    def check_integrity(self) -> List[str]:
        """Sorun listesi; boş liste her iki veritabanının da sağlam olduğunu gösterir."""
        errors: List[str] = []
        try:
            conn = sqlite3.connect(str(self.sqlite_path), timeout=5)
            try:
                result = conn.execute("PRAGMA integrity_check;").fetchone()
            finally:
                conn.close()
            if not result or result[0] != "ok":
                errors.append(f"SQLite Bütünlük Sorunu: {result}")
        except Exception as exc:
            errors.append(f"SQLite Kontrol Hatası: {exc}")

        try:
            conn = duckdb.connect(str(self.duckdb_path), read_only=True)
            try:
                count = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
            finally:
                conn.close()
            if count <= 0:
                errors.append("DuckDB: Tablo boş veya hasarlı.")
        except Exception as exc:
            errors.append(f"DuckDB Kontrol Hatası: {exc}")
        return errors

    # ---- dışa aktarım -------------------------------------------------------------------
    def export_backup_data(self) -> Dict[str, Any]:
        """Hisse, işlem, nakit hareketi ve izleme listesi tablolarının JSON'a uygun dökümü."""
        import pandas as pd

        conn = sqlite3.connect(str(self.sqlite_path), timeout=5)
        try:
            data: Dict[str, Any] = {"version": "2.0.0", "exported_at": datetime.now().isoformat()}
            for table in _BACKUP_TABLES:
                data[table] = pd.read_sql_query(f"SELECT * FROM {table}", conn).to_dict(orient="records")
        finally:
            conn.close()
        return data

    def export_tables_to_excel(self, target_file: Path) -> None:
        """Doğrudan SQLite tablolarından basit Excel dökümü (kapsamlı rapor servisi yoksa yedek yol)."""
        import pandas as pd

        conn = sqlite3.connect(str(self.sqlite_path), timeout=5)
        try:
            frames = {
                "Mevcut Pozisyonlar": pd.read_sql_query("SELECT * FROM stocks", conn),
                "İşlem Geçmişi": pd.read_sql_query("SELECT * FROM trades ORDER BY trade_date DESC", conn),
                "Nakit Hareketleri": pd.read_sql_query("SELECT * FROM cash_movements ORDER BY movement_date DESC", conn),
            }
        finally:
            conn.close()
        with pd.ExcelWriter(str(target_file), engine="openpyxl") as writer:
            for sheet, frame in frames.items():
                frame.to_excel(writer, sheet_name=sheet, index=False)
