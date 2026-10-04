"""Sürümlü şema göçleri: sürüm kaydı, göç öncesi yedek, hata yükseltme ve taze veritabanı (gerçek geçici SQLite)."""
from __future__ import annotations

import sqlite3

import pytest

from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy import schema_migrations
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import Base
from src.infrastructure.db.sqlalchemy.schema_migrations import (
    BACKUP_PREFIX,
    KEEP_BACKUPS,
    Migration,
    SchemaMigrationError,
    run_migrations,
)

OLD_CASH_MOVEMENTS = """
    CREATE TABLE cash_movements (
        id BIGINT NOT NULL, movement_date DATE NOT NULL, movement_time TIME, type VARCHAR(8) NOT NULL,
        amount NUMERIC(18, 4) NOT NULL, notes VARCHAR(255),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id)
    )
"""


def _versions(path) -> list[int]:
    with sqlite3.connect(path) as conn:
        return [row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]


def _backups(path):
    return sorted((path.parent / "backups").glob(f"{BACKUP_PREFIX}*.db"))


def _old_database(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.execute(OLD_CASH_MOVEMENTS)
        conn.execute(
            "INSERT INTO cash_movements (id, movement_date, type, amount) VALUES (1, '2026-01-01', 'DEPOSIT', 100)"
        )
    return path


def test_fresh_database_records_all_migrations_without_backup(tmp_path):
    path = tmp_path / "fresh.db"

    SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path))).dispose()

    assert _versions(path) == [m.version for m in schema_migrations.MIGRATIONS]
    assert _backups(path) == []


def test_existing_database_is_backed_up_and_migrated_once(tmp_path):
    path = _old_database(tmp_path)

    SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path))).dispose()

    assert _versions(path) == [1, 2, 3]
    backups = _backups(path)
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute("SELECT amount FROM cash_movements").fetchall() == [(100,)]
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cash_movements)")}
    assert "stock_id" not in columns


def test_second_startup_applies_nothing_and_takes_no_new_backup(tmp_path):
    path = _old_database(tmp_path)
    SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path))).dispose()
    first_backups = _backups(path)

    SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path))).dispose()

    assert _backups(path) == first_backups
    assert _versions(path) == [1, 2, 3]


def test_migration_runs_exactly_once(tmp_path):
    path = _old_database(tmp_path)
    calls = []
    extra = Migration(99, "probe", lambda conn: calls.append(1))
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path)))

    run_migrations(provider._engine, Base.metadata, schema_migrations.MIGRATIONS + (extra,))
    run_migrations(provider._engine, Base.metadata, schema_migrations.MIGRATIONS + (extra,))

    assert calls == [1]
    provider.dispose()


def test_failing_migration_raises_keeps_backup_and_is_not_recorded(tmp_path):
    path = _old_database(tmp_path)
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path)))

    def boom(conn):
        raise RuntimeError("bozuk göç")

    broken = Migration(50, "broken", boom)
    before_backups = len(_backups(path))

    with pytest.raises(SchemaMigrationError, match="50"):
        run_migrations(provider._engine, Base.metadata, schema_migrations.MIGRATIONS + (broken,))

    assert 50 not in _versions(path)
    assert len(_backups(path)) == before_backups + 1
    provider.dispose()


def test_backup_failure_aborts_before_any_migration(tmp_path, monkeypatch):
    path = _old_database(tmp_path)

    def fail_backup(db_path):
        raise SchemaMigrationError("disk dolu")

    monkeypatch.setattr(schema_migrations, "_backup_database", fail_backup)

    with pytest.raises(SchemaMigrationError, match="disk dolu"):
        SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(path)))

    with sqlite3.connect(path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(cash_movements)")}
    assert "stock_id" not in columns


def test_old_backups_are_pruned(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for index in range(KEEP_BACKUPS + 3):
        (backup_dir / f"{BACKUP_PREFIX}20260101_0000{index:02d}.db").write_bytes(b"x")

    schema_migrations._prune_backups(backup_dir)

    remaining = sorted(p.name for p in backup_dir.glob(f"{BACKUP_PREFIX}*.db"))
    assert len(remaining) == KEEP_BACKUPS
    assert remaining[-1].endswith(f"{KEEP_BACKUPS + 2:02d}.db")
