"""scripts/rebuild_sqlite_prices.py: tekil sapma onarılır, faktör izi taşıyan hisse ve hayalet referans atlanır."""
import importlib.util
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "rebuild_sqlite_prices.py"
spec = importlib.util.spec_from_file_location("rebuild_sqlite_prices", SCRIPT)
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r  # dataclass modül kaydını ister
spec.loader.exec_module(r)

from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository  # noqa: E402

DAYS = [date(2026, 3, 2) + timedelta(days=i) for i in range(12) if (date(2026, 3, 2) + timedelta(days=i)).weekday() < 5]


def _setup(tmp_path):
    duck_path, lite_path = tmp_path / "m.duckdb", tmp_path / "p.db"
    con = duckdb.connect(str(duck_path))
    con.execute("CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
                "low_price DOUBLE, close_price DOUBLE, volume BIGINT)")
    rows = [("AAA", d, 10, 10.5, 9.5, 10.0, 1000) for d in DAYS]
    rows += [("BBB", d, 10, 10.5, 9.5, 10.0, 1000) for d in DAYS]
    rows[3] = ("AAA", DAYS[3], 10, 10, 10, 10.0, 0)  # hacimsiz referans: kullanılmaz
    con.executemany("INSERT INTO daily_prices VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()
    lite = sqlite3.connect(lite_path)
    lite.execute("CREATE TABLE stocks (id INTEGER, ticker TEXT)")
    lite.execute("CREATE TABLE daily_prices (id INTEGER, stock_id INTEGER, price_date TEXT, close_price REAL, "
                 "open_price REAL, high_price REAL, low_price REAL, volume INTEGER, source TEXT)")
    lite.executemany("INSERT INTO stocks VALUES (?, ?)", [(1, "AAA"), (2, "BBB")])
    data, row_id = [], 1
    for i, d in enumerate(DAYS):
        aaa = 9.8 if i == 1 else (7.0 if i == 3 else 10.0)  # gün 1 temettü-düzeltmeli sıçrama, gün 3 SQLite doğru
        for sid, close in ((1, aaa), (2, 7.5)):            # BBB her gün %25 farklı: faktör izi
            data.append((row_id, sid, d.isoformat(), close, None, None, None, None, "yfinance"))
            row_id += 1
    lite.executemany("INSERT INTO daily_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
    lite.commit()
    lite.close()
    return duck_path, lite_path


def test_isolated_deviation_fixed_systematic_and_ghost_reference_skipped(tmp_path):
    duck_path, lite_path = _setup(tmp_path)
    plans = r.build_plans(lite_path, DuckDBMarketHistoryRepository(duck_path))
    by = {p.ticker: p for p in plans}
    assert [u[7] for u in by["AAA"].updates] == [DAYS[1]] and not by["AAA"].systematic(0.10)
    assert by["BBB"].systematic(0.10)

    assert r.execute(lite_path, plans, 0.10) == 1

    lite = sqlite3.connect(lite_path)
    closes = dict(lite.execute("SELECT price_date, close_price FROM daily_prices WHERE stock_id = 1"))
    bbb = {c for (c,) in lite.execute("SELECT close_price FROM daily_prices WHERE stock_id = 2")}
    lite.close()
    assert closes[DAYS[1].isoformat()] == 10.0 and closes[DAYS[3].isoformat()] == 7.0
    assert bbb == {7.5}
