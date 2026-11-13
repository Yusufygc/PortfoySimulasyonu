"""scripts/clean_ghost_bars.py: geçici DuckDB ve SQLite kopyalarında kuru çalıştırma ve uygulama."""
import importlib.util
import sqlite3
from datetime import date
from pathlib import Path

import duckdb

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "clean_ghost_bars.py"
spec = importlib.util.spec_from_file_location("clean_ghost_bars", SCRIPT)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def _make_dbs(tmp_path):
    duck_path, lite_path = tmp_path / "m.duckdb", tmp_path / "p.db"
    con = duckdb.connect(str(duck_path))
    con.execute("CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
                "low_price DOUBLE, close_price DOUBLE, volume BIGINT)")
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR, first_date DATE, last_date DATE, total_bars INTEGER)")
    con.executemany("INSERT INTO daily_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [
        ("ASELS", date(2026, 5, 26), 10, 11, 9, 10.5, 1000),
        ("ASELS", date(2026, 5, 27), 10.5, 10.5, 10.5, 10.5, 0),   # bayram
        ("ASELS", date(2026, 6, 2), 10.6, 11, 10.4, 10.9, 2000),
    ])
    con.execute("INSERT INTO bist_stocks VALUES ('ASELS', '2026-05-26', '2026-06-02', 3)")
    con.close()
    lite = sqlite3.connect(lite_path)
    lite.execute("CREATE TABLE stocks (id INTEGER, ticker TEXT)")
    lite.execute("CREATE TABLE daily_prices (id INTEGER, stock_id INTEGER, price_date TEXT, open_price REAL, "
                 "high_price REAL, low_price REAL, close_price REAL, volume INTEGER)")
    lite.execute("INSERT INTO stocks VALUES (1, 'ASELS')")
    lite.executemany("INSERT INTO daily_prices VALUES (?, 1, ?, NULL, NULL, NULL, ?, NULL)", [
        (1, "2026-05-26", 10.5), (2, "2026-05-30", 10.5), (3, "2026-06-02", 10.9),  # 30.05 Cumartesi
    ])
    lite.commit()
    lite.close()
    return duck_path, lite_path


def test_dry_run_finds_and_execute_removes_ghosts(tmp_path):
    duck_path, lite_path = _make_dbs(tmp_path)
    con = duckdb.connect(str(duck_path), read_only=True)
    duck = g.duckdb_ghosts(con)
    con.close()
    lite = sqlite3.connect(lite_path)
    sqlite_ids = g.sqlite_ghosts(lite)
    lite.close()
    assert duck == [("ASELS", date(2026, 5, 27))] and sqlite_ids == [2]

    g.execute(duck_path, lite_path, duck, sqlite_ids)

    con = duckdb.connect(str(duck_path), read_only=True)
    assert con.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0] == 2
    assert con.execute("SELECT total_bars FROM bist_stocks").fetchone()[0] == 2
    con.close()
    lite = sqlite3.connect(lite_path)
    assert [r[0] for r in lite.execute("SELECT id FROM daily_prices ORDER BY id")] == [1, 3]
    lite.close()
    assert len(list((tmp_path / "backups").iterdir())) == 2
