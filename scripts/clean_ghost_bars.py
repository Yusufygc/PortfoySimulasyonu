"""
clean_ghost_bars.py — DuckDB piyasa geçmişinden ve SQLite `daily_prices` tablosundan hayalet barları siler.

Hayalet bar: BIST'in kapalı olduğu gün (2020+ tatil takvimi) veya hacmi 0, açılış = yüksek = düşük = kapanış olan bar
(`src/infrastructure/market_data/bar_quality.py`). İndiriciler artık bu barları yazmaz; bu betik geçmişte yazılmış
olanları temizler. SQLite satırları yalnızca kendi verisine göre silinir (OHLCV yoksa yalnızca takvim kuralı); DuckDB'de
hayalet olan bir gün SQLite'ta başka bir indirmeden gelmiş gerçek kapanış olabilir (ör. 11.03.2020), bu yüzden
DuckDB eşleşmesi SQLite silme gerekçesi değildir. Varsayılan KURU ÇALIŞTIRMADIR (hiçbir şey değişmez).

Kullanım:
    python scripts/clean_ghost_bars.py                                # yalnızca rapor
    python scripts/clean_ghost_bars.py --execute                      # iki veritabanının yedeğini alır, sonra siler
    python scripts/clean_ghost_bars.py --sqlite kopya.db --duckdb kopya.duckdb
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import duckdb  # noqa: E402

from src.infrastructure.db.paths import app_root  # noqa: E402
from src.infrastructure.market_data.bar_quality import is_ghost_bar  # noqa: E402


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def duckdb_ghosts(con) -> list[tuple[str, date]]:
    rows = con.execute(
        "SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices"
    ).fetchall()
    return [(r[0], _as_date(r[1])) for r in rows if is_ghost_bar(_as_date(r[1]), tuple(r[2:7]))]


def sqlite_ghosts(con) -> list[int]:
    """Silinecek SQLite `daily_prices.id` listesi (satırın kendi OHLCV'si veya takvim kuralı)."""
    rows = con.execute(
        "SELECT dp.id, s.ticker, dp.price_date, dp.open_price, dp.high_price, dp.low_price, dp.close_price, dp.volume "
        "FROM daily_prices dp JOIN stocks s ON s.id = dp.stock_id"
    ).fetchall()
    ids = []
    for row_id, _ticker, raw_date, *ohlcv in rows:
        day = _as_date(raw_date)
        known = None not in ohlcv[:4]
        close = ohlcv[3]
        bar = tuple(ohlcv) if known else (close, close, close, close, None)  # OHLCV yoksa yalnızca takvim kuralı
        if is_ghost_bar(day, bar):
            ids.append(row_id)
    return ids


def backup(path: Path, label: str) -> Path:
    target = path.parent / "backups" / f"{path.stem}_pre_ghost_cleanup_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".db":
        src, dst = sqlite3.connect(path), sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
    else:
        shutil.copy2(path, target)
    print(f"{label} yedeği: {target}")
    return target


def report(duck: list[tuple[str, date]], sqlite_ids: list[int]) -> None:
    by_date = Counter(d for _, d in duck)
    print(f"DuckDB hayalet bar: {len(duck)} ({len({t for t, _ in duck})} hisse)")
    print("En çok etkilenen günler:", ", ".join(f"{d:%d.%m.%Y} ({n})" for d, n in by_date.most_common(8)))
    print(f"SQLite daily_prices silinecek satır: {len(sqlite_ids)}")


def recompute_stats(con) -> None:
    con.execute(
        "UPDATE bist_stocks SET first_date = s.first_date, last_date = s.last_date, total_bars = s.total_bars "
        "FROM (SELECT ticker, MIN(price_date) AS first_date, MAX(price_date) AS last_date, COUNT(*) AS total_bars "
        "FROM daily_prices GROUP BY ticker) s WHERE bist_stocks.ticker = s.ticker"
    )


def execute(duck_path: Path, sqlite_path: Path, duck: list, sqlite_ids: list[int]) -> None:
    backup(duck_path, "DuckDB")
    backup(sqlite_path, "SQLite")
    con = duckdb.connect(str(duck_path))
    try:
        con.executemany("DELETE FROM daily_prices WHERE ticker = ? AND price_date = ?", duck)
        recompute_stats(con)
    finally:
        con.close()
    lite = sqlite3.connect(sqlite_path)
    try:
        lite.executemany("DELETE FROM daily_prices WHERE id = ?", [(i,) for i in sqlite_ids])
        lite.commit()
    finally:
        lite.close()
    print("Temizlik tamamlandı.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hayalet (tatil / hacimsiz sabit) barları siler.")
    parser.add_argument("--sqlite", type=Path, default=app_root() / "data" / "portfolio.db")
    parser.add_argument("--duckdb", type=Path, default=app_root() / "data" / "market_history.duckdb")
    parser.add_argument("--execute", action="store_true", help="Yedek alıp siler (varsayılan: yalnızca rapor).")
    args = parser.parse_args()
    print(f"SQLite: {args.sqlite.resolve()}\nDuckDB: {args.duckdb.resolve()}")

    con = duckdb.connect(str(args.duckdb), read_only=True)
    try:
        duck = duckdb_ghosts(con)
    finally:
        con.close()
    lite = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
    try:
        sqlite_ids = sqlite_ghosts(lite)
    finally:
        lite.close()
    report(duck, sqlite_ids)
    if args.execute:
        execute(args.duckdb, args.sqlite, duck, sqlite_ids)
    else:
        print("Kuru çalıştırma: hiçbir şey değişmedi. Uygulamak için --execute.")


if __name__ == "__main__":
    main()
