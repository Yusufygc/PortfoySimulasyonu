"""Numaralı SQLite şema göçleri.

`create_all` yalnızca eksik tabloları kurar; mevcut tabloya sütun eklemez veya veri dönüştürmez. Bu modül
bu işleri sürümlü yapar:

- Uygulanan göçler `schema_migrations` tablosunda tutulur; her göç yalnızca bir kez çalışır.
- Bekleyen göç varsa ve veritabanı dolu ise, göçten önce `<veri dizini>/backups/` altına tutarlı bir yedek alınır
  (SQLite `backup` API'si). Yedek alınamazsa göç başlamaz.
- Her göç kendi transaction'ında çalışır ve sürüm kaydı aynı transaction'da yazılır. SQLite DDL'i her sürücüde
  geri alınamayabileceğinden göç fonksiyonları **idempotent** yazılmalıdır.
- Hata yutulmaz: `SchemaMigrationError` yükselir ve uygulama bozuk şemayla açılmaz.

Yeni göç eklemek için `MIGRATIONS` listesinin sonuna bir sonraki numarayla `Migration` ekleyin; mevcut numaraları
veya sırayı değiştirmeyin.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from sqlalchemy import MetaData, inspect
from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)

VERSION_TABLE = "schema_migrations"
BACKUP_PREFIX = "portfolio_pre_migration_"
KEEP_BACKUPS = 5


class SchemaMigrationError(RuntimeError):
    """Şema göçü veya göç öncesi yedek başarısız oldu."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Connection], None]


def _drop_legacy_golden_cross_events(conn: Connection) -> None:
    """Türetilmiş veri: eski `stock_id` anahtarlı tablo yerine ticker anahtarlı `cross_events` kullanılır."""
    conn.exec_driver_sql("DROP TABLE IF EXISTS golden_cross_events")


def _canonicalize_stock_tickers(conn: Connection) -> None:
    """Kanonik ticker uzantısızdır: eski `.IS` kayıtlar çakışma yoksa uzantısıza çevrilir."""
    conn.exec_driver_sql(
        "UPDATE stocks SET ticker = substr(ticker, 1, length(ticker) - 3) "
        "WHERE upper(ticker) LIKE '%.IS' AND NOT EXISTS ("
        "SELECT 1 FROM stocks s2 WHERE s2.ticker = substr(stocks.ticker, 1, length(stocks.ticker) - 3))"
    )


def _add_cash_movements_stock_id(conn: Connection) -> None:
    """Temettü kaydı için `cash_movements.stock_id` (nullable) sütununu ekler."""
    columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(cash_movements)")}
    if columns and "stock_id" not in columns:
        conn.exec_driver_sql(
            "ALTER TABLE cash_movements ADD COLUMN stock_id BIGINT REFERENCES stocks(id) ON DELETE SET NULL"
        )


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "drop_legacy_golden_cross_events", _drop_legacy_golden_cross_events),
    Migration(2, "canonicalize_stock_tickers", _canonicalize_stock_tickers),
    Migration(3, "add_cash_movements_stock_id", _add_cash_movements_stock_id),
)


def _ensure_version_table(conn: Connection) -> None:
    conn.exec_driver_sql(
        f"CREATE TABLE IF NOT EXISTS {VERSION_TABLE} ("
        "version INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, applied_at VARCHAR(32) NOT NULL)"
    )


def _record(conn: Connection, migration: Migration) -> None:
    conn.exec_driver_sql(
        f"INSERT INTO {VERSION_TABLE} (version, name, applied_at) VALUES (?, ?, ?)",
        (migration.version, migration.name, datetime.now().isoformat(timespec="seconds")),
    )


def _applied_versions(engine: Engine, existing_tables: set[str]) -> set[int]:
    if VERSION_TABLE not in existing_tables:
        return set()
    with engine.connect() as conn:
        return {row[0] for row in conn.exec_driver_sql(f"SELECT version FROM {VERSION_TABLE}")}


def _database_file(engine: Engine) -> Path | None:
    database = engine.url.database
    if not database or database == ":memory:":
        return None
    return Path(database)


def _prune_backups(backup_dir: Path) -> None:
    backups = sorted(backup_dir.glob(f"{BACKUP_PREFIX}*.db"))
    for old in backups[:-KEEP_BACKUPS]:
        try:
            old.unlink()
        except OSError as exc:
            logger.warning("Eski göç yedeği silinemedi (%s): %s", old, exc)


def _backup_database(db_path: Path) -> Path:
    backup_dir = db_path.parent / "backups"
    target = backup_dir / f"{BACKUP_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(str(db_path))
        destination = sqlite3.connect(str(target))
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
    except (OSError, sqlite3.Error) as exc:
        raise SchemaMigrationError(f"Göç öncesi yedek alınamadı ({target}): {exc}") from exc
    _prune_backups(backup_dir)
    return target


def run_migrations(
    engine: Engine,
    metadata: MetaData,
    migrations: tuple[Migration, ...] = MIGRATIONS,
) -> None:
    """Şemayı kurar ve bekleyen göçleri sırayla uygular; hata `SchemaMigrationError` olarak yükselir."""
    existing_tables = set(inspect(engine).get_table_names())
    is_fresh = not existing_tables
    pending = [] if is_fresh else [
        m for m in sorted(migrations, key=lambda m: m.version)
        if m.version not in _applied_versions(engine, existing_tables)
    ]

    backup_path: Path | None = None
    db_path = _database_file(engine)
    if pending and db_path is not None:
        backup_path = _backup_database(db_path)
        logger.info("Şema göçü öncesi yedek alındı: %s", backup_path)

    try:
        metadata.create_all(bind=engine, checkfirst=True)
        with engine.begin() as conn:
            _ensure_version_table(conn)
            if is_fresh:
                # Taze veritabanında create_all güncel şemayı kurar; geçmiş göçler uygulanmış sayılır.
                for migration in sorted(migrations, key=lambda m: m.version):
                    _record(conn, migration)
    except Exception as exc:
        raise SchemaMigrationError(f"Şema oluşturulamadı: {exc}") from exc

    for migration in pending:
        try:
            with engine.begin() as conn:
                migration.apply(conn)
                _record(conn, migration)
        except Exception as exc:
            backup_note = f" Yedek: {backup_path}" if backup_path else ""
            raise SchemaMigrationError(
                f"Şema göçü {migration.version} ({migration.name}) başarısız: {exc}.{backup_note}"
            ) from exc
        logger.info("Şema göçü uygulandı: %s (%s)", migration.version, migration.name)
