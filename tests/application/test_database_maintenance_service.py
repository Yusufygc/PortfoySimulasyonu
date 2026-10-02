"""DatabaseMaintenanceService: istatistik, bütünlük kontrolü ve yedek dökümü."""
from __future__ import annotations

import sqlite3
from datetime import date

import duckdb

from src.application.services.database.database_maintenance_service import (
    DatabaseMaintenanceService,
    format_file_size,
)


def _make_sqlite(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE stocks (id INTEGER PRIMARY KEY, ticker TEXT)")
    conn.execute("CREATE TABLE trades (id INTEGER PRIMARY KEY, trade_date TEXT)")
    conn.execute("CREATE TABLE cash_movements (id INTEGER PRIMARY KEY, movement_date TEXT)")
    conn.execute("CREATE TABLE watchlists (id INTEGER PRIMARY KEY, name TEXT)")
    conn.executemany("INSERT INTO stocks (ticker) VALUES (?)", [("THYAO",), ("ASELS",)])
    conn.commit()
    conn.close()


def _make_duckdb(path, rows=3):
    conn = duckdb.connect(str(path))
    conn.execute("CREATE TABLE bist_stocks (ticker VARCHAR)")
    conn.execute("CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE)")
    conn.execute("INSERT INTO bist_stocks VALUES ('THYAO')")
    for day in range(rows):
        conn.execute("INSERT INTO daily_prices VALUES ('THYAO', ?)", [date(2026, 1, 1 + day)])
    conn.close()


def test_format_file_size_units():
    assert format_file_size(512) == "512 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(3 * 1024 * 1024) == "3.00 MB"


def test_collect_stats_reads_both_databases(tmp_path):
    _make_sqlite(tmp_path / "p.db")
    _make_duckdb(tmp_path / "m.duckdb", rows=3)
    service = DatabaseMaintenanceService(tmp_path / "p.db", tmp_path / "m.duckdb")

    stats = service.collect_stats()

    by_name = {row["name"]: row["count"] for row in stats["sqlite_table_stats"]}
    assert by_name["Hisse Senetleri (Katalog)"] == "2" and by_name["Finansal Hedefler (Planning)"] == "0"
    assert stats["duckdb_stock_count"] == 1 and stats["duckdb_total_bars"] == "3"
    assert stats["duckdb_last_date"] == "03.01.2026"
    assert stats["duckdb_is_up_to_date"] is True


def test_collect_stats_reports_missing_files(tmp_path):
    stats = DatabaseMaintenanceService(tmp_path / "yok.db", tmp_path / "yok.duckdb").collect_stats()

    assert stats["sqlite_size"] == "0 B (Dosya Yok)" and stats["sqlite_table_stats"] == []
    assert stats["duckdb_size"] == "0 B (Dosya Yok)" and stats["duckdb_is_up_to_date"] is False


def test_integrity_check_passes_and_flags_empty_duckdb(tmp_path):
    _make_sqlite(tmp_path / "p.db")
    _make_duckdb(tmp_path / "m.duckdb", rows=2)
    assert DatabaseMaintenanceService(tmp_path / "p.db", tmp_path / "m.duckdb").check_integrity() == []

    _make_duckdb(tmp_path / "bos.duckdb", rows=0)
    errors = DatabaseMaintenanceService(tmp_path / "p.db", tmp_path / "bos.duckdb").check_integrity()
    assert errors == ["DuckDB: Tablo boş veya hasarlı."]


def test_export_backup_data_dumps_catalog_tables(tmp_path):
    _make_sqlite(tmp_path / "p.db")
    service = DatabaseMaintenanceService(tmp_path / "p.db", tmp_path / "m.duckdb")

    data = service.export_backup_data()

    assert data["version"] == "2.0.0" and [row["ticker"] for row in data["stocks"]] == ["THYAO", "ASELS"]
    assert data["trades"] == [] and data["watchlists"] == []
