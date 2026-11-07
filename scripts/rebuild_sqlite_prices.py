"""
rebuild_sqlite_prices.py — SQLite `daily_prices` kapanışlarını DuckDB piyasa geçmişiyle (ham + onaylı faktör) onarır.

Neden: SQLite'a eskiden iki yoldan fiyat yazıldı: piyasa senkronu ham kapanış, fiyat sağlığı/backfill ise
temettü-düzeltmeli Yahoo kapanışı. Sonuç: tek günlük sahte sıçramalar (ör. UNLU 05.01.2023: 9,77, ham 10,26).

Kural:
- Bir hissede DuckDB ile çakışan satırların çoğu uyumluysa, %0,5'ten fazla sapan satırlar DuckDB değeriyle
  (kapanış ve varsa OHLC + hacim) değiştirilir.
- Sapma faktör izi taşıyorsa (çakışan satırların `--systematic` oranından fazlası farklı VE SQLite/DuckDB oran
  medyanı 1'den %5'ten fazla uzak), hisse DEĞİŞTİRİLMEZ ve rapora yazılır: bu genellikle DuckDB'de onaylanmamış
  bir sermaye artırımı faktörüdür; kör onarım doğru SQLite düzeltmesini geri alırdı. Önce Ayarlar > Piyasa
  Düzeltmeleri'nden olay onaylanmalıdır. Oran medyanı ~1 olan yaygın sapma temettü düzeltmesi karışımıdır, onarılır.
- DuckDB'deki hayalet bar (tatil, hacimsiz sabit fiyat) ve hacmi 0 olan bar referans alınmaz; o gün SQLite'taki
  değer korunur.
- Yalnızca SQLite'ta olan günlere dokunulmaz.
Varsayılan KURU ÇALIŞTIRMADIR (hiçbir şey değişmez).

Kullanım:
    python scripts/rebuild_sqlite_prices.py                       # yalnızca rapor
    python scripts/rebuild_sqlite_prices.py --execute             # SQLite yedeğini alır, sonra onarır
    python scripts/rebuild_sqlite_prices.py --sqlite kopya.db --duckdb kopya.duckdb
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure.db.paths import app_root  # noqa: E402
from src.infrastructure.market_data.bar_quality import is_ghost_bar  # noqa: E402
from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository  # noqa: E402

TOLERANCE = 0.005
FACTOR_TRACE = 0.05  # oran medyanı 1'den bu kadar uzaksa sapma bir sermaye artırımı faktörüdür


@dataclass
class StockPlan:
    ticker: str
    overlap: int = 0
    updates: list = field(default_factory=list)  # (row_id, close, open, high, low, volume, eski kapanış, gün)

    def median_ratio(self) -> float:
        ratios = sorted(u[6] / u[1] for u in self.updates)
        return ratios[len(ratios) // 2] if ratios else 1.0

    def systematic(self, share: float) -> bool:
        widespread = self.overlap > 0 and len(self.updates) / self.overlap > share
        return widespread and abs(self.median_ratio() - 1.0) > FACTOR_TRACE


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _is_ghost(bar) -> bool:
    """Referans alınmayacak DuckDB barı: hayalet bar veya hacmi 0 (Yahoo bu günlerde bozuk değer döndürebilir,
    ör. TATGD 09.04.2024 ham sütunda zaten düzeltilmiş fiyat)."""
    if bar.volume == 0:
        return True
    return is_ghost_bar(bar.price_date, (bar.open_price, bar.high_price, bar.low_price, bar.close_price, bar.volume))


def plan_stock(con, history, stock_id: int, ticker: str) -> StockPlan:
    plan = StockPlan(ticker)
    rows = con.execute("SELECT id, price_date, close_price FROM daily_prices WHERE stock_id = ?", (stock_id,)).fetchall()
    if not rows:
        return plan
    days = [_as_date(r[1]) for r in rows]
    bars = {b.price_date: b for b in history.get_price_series(ticker, min(days), max(days))}
    for (row_id, _raw, close), day in zip(rows, days):
        bar = bars.get(day)
        if bar is None or not close or bar.close_price <= 0 or _is_ghost(bar):
            continue
        plan.overlap += 1
        if abs(float(close) / bar.close_price - 1.0) > TOLERANCE:
            plan.updates.append((row_id, bar.close_price, bar.open_price, bar.high_price, bar.low_price, bar.volume,
                                 float(close), day))
    return plan


def build_plans(sqlite_path: Path, history) -> list[StockPlan]:
    con = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    try:
        stocks = con.execute("SELECT id, ticker FROM stocks").fetchall()
        return [plan_stock(con, history, sid, (t or "").replace(".IS", "").upper()) for sid, t in stocks]
    finally:
        con.close()


def report(plans: list[StockPlan], share: float) -> None:
    fix = [p for p in plans if p.updates and not p.systematic(share)]
    skip = [p for p in plans if p.systematic(share)]
    print(f"Onarılacak: {sum(len(p.updates) for p in fix)} satır, {len(fix)} hisse")
    for p in sorted(fix, key=lambda p: -len(p.updates))[:15]:
        worst = max(p.updates, key=lambda u: abs(u[6] / u[1] - 1))
        print(f"  {p.ticker}: {len(p.updates)}/{p.overlap} satır; en büyük sapma {worst[7]:%d.%m.%Y} "
              f"{worst[6]:.4f} -> {worst[1]:.4f}")
    print(f"Sistematik sapma (değiştirilmedi, inceleyin): {len(skip)} hisse")
    for p in sorted(skip, key=lambda p: -len(p.updates)):
        print(f"  {p.ticker}: {len(p.updates)}/{p.overlap} satır farklı, SQLite/DuckDB oran medyanı {p.median_ratio():.4f}")


def backup(path: Path) -> Path:
    target = path.parent / "backups" / f"{path.stem}_pre_price_rebuild_{datetime.now():%Y%m%d_%H%M%S}.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    src, dst = sqlite3.connect(path), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    print(f"SQLite yedeği: {target}")
    return target


def execute(sqlite_path: Path, plans: list[StockPlan], share: float) -> int:
    backup(sqlite_path)
    rows = [u for p in plans if not p.systematic(share) for u in p.updates]
    con = sqlite3.connect(sqlite_path)
    try:
        con.executemany(
            "UPDATE daily_prices SET close_price = ?, open_price = COALESCE(?, open_price), "
            "high_price = COALESCE(?, high_price), low_price = COALESCE(?, low_price), "
            "volume = COALESCE(?, volume), source = 'duckdb_rebuild' WHERE id = ?",
            [(u[1], u[2], u[3], u[4], u[5], u[0]) for u in rows],
        )
        con.commit()
    finally:
        con.close()
    print(f"Onarıldı: {len(rows)} satır.")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite fiyatlarını DuckDB piyasa geçmişiyle onarır.")
    parser.add_argument("--sqlite", type=Path, default=app_root() / "data" / "portfolio.db")
    parser.add_argument("--duckdb", type=Path, default=app_root() / "data" / "market_history.duckdb")
    parser.add_argument("--systematic", type=float, default=0.10,
                        help="Bu orandan fazla satırı farklı olan hisse sistematik sayılır ve atlanır.")
    parser.add_argument("--execute", action="store_true", help="Yedek alıp onarır (varsayılan: yalnızca rapor).")
    args = parser.parse_args()
    print(f"SQLite: {args.sqlite.resolve()}\nDuckDB: {args.duckdb.resolve()}")
    plans = build_plans(args.sqlite, DuckDBMarketHistoryRepository(args.duckdb))
    report(plans, args.systematic)
    if args.execute:
        execute(args.sqlite, plans, args.systematic)
    else:
        print("Kuru çalıştırma: hiçbir şey değişmedi. Uygulamak için --execute.")


if __name__ == "__main__":
    main()
