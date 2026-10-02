"""
migrate_market_universe_to_duckdb.py — SQLite'taki piyasa fiyat geçmişini DuckDB tek evrenine taşır.

Kullanıcı verisine (işlem, izleme listesi, model portföy, kurumsal aksiyon) bağlı olmayan hisselerin SQLite fiyat
geçmişi ve kayıtları silinir; silmeden önce SQLite'taki düzeltilmiş geçmişten geçmiş sermaye artırımları türetilip
DuckDB'ye onaylı olay olarak yazılır. Varsayılan KURU ÇALIŞTIRMADIR (hiçbir şey değişmez).

Kullanım:
    python scripts/migrate_market_universe_to_duckdb.py              # yalnızca plan raporu
    python scripts/migrate_market_universe_to_duckdb.py --execute    # yedek alır, sonra uygular
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.application.container import AppContainer
from src.application.services.market_data.market_universe_migration_service import MarketUniverseMigrationService
from src.infrastructure.db.paths import sqlite_db_path


def backup_sqlite(db_path: Path) -> Path:
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{db_path.stem}_pre_universe_migration_{datetime.now():%Y%m%d_%H%M%S}.db"
    src, dst = sqlite3.connect(db_path), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite piyasa fiyat geçmişini DuckDB'ye taşır.")
    parser.add_argument("--execute", action="store_true", help="Yedek alır ve değişiklikleri uygular (varsayılan: kuru çalıştırma)")
    args = parser.parse_args()

    container = AppContainer()
    repos = container.repositories
    service = MarketUniverseMigrationService(
        stock_repo=repos.stock_repo,
        price_repo=repos.price_repo,
        maintenance_repo=repos.portfolio_maintenance_repo,
        market_history_repo=repos.market_history_repo,
        market_action_service=container.services.market_corporate_action_service,
    )
    plan = service.plan()
    print(f"Toplam SQLite hissesi : {len(plan.entries)}")
    print(f"Kullanıcı verisine bağlı (kalır)     : {len(plan.kept_referenced)}")
    print(f"Silinecek (referanssız + DuckDB'de var): {len(plan.deletable)}  "
          f"({sum(e.sqlite_bars for e in plan.deletable):,} fiyat satırı)")
    print(f"Referanssız ama DuckDB kapsamıyor (kalır): {len(plan.kept_uncovered)}")
    for entry in plan.kept_uncovered:
        print(f"  ! {entry.ticker}: SQLite {entry.sqlite_bars} bar, DuckDB {entry.duckdb_bars} bar")

    if not args.execute:
        print("\nKuru çalıştırma: hiçbir şey değişmedi. Uygulamak için --execute ekleyin.")
        return

    backup = backup_sqlite(sqlite_db_path(os.getenv("DB_SQLITE_PATH")))
    print(f"\nYedek alındı: {backup}")
    result = service.execute(plan)
    print(f"DuckDB'ye türetilen sermaye artırımı : {result.derived_actions}")
    print(f"Silinen fiyat satırı / hisse         : {result.deleted_prices:,} / {result.deleted_stocks}")
    for error in result.errors:
        print(f"  ! {error}")


if __name__ == "__main__":
    main()
