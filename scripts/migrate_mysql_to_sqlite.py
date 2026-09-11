from __future__ import annotations

import sys
import argparse
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, MetaData, select, insert, delete, event

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.infrastructure.db.sqlalchemy.orm_models import Base  # noqa: E402

CRITICAL_TABLES = ("trades", "daily_prices")


def load_env_dict(env_name: str = "") -> dict:
    filename = f".env.{env_name}" if env_name else ".env"
    env_path = ROOT / filename
    if not env_path.exists():
        print(f"Hata: {filename} dosyası bulunamadı!")
        sys.exit(1)
    return dotenv_values(env_path)


def make_mysql_url(env_data: dict) -> tuple[str, str, str]:
    host = env_data.get("DB_HOST")
    port = env_data.get("DB_PORT")
    user = env_data.get("DB_USER")
    password = env_data.get("DB_PASSWORD")
    database = env_data.get("DB_NAME")
    if not all([host, port, user, password, database]):
        print("Hata: Gerekli MySQL bağlantı parametreleri eksik!")
        sys.exit(1)
    url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
    return url, host, database


def resolve_sqlite_path(args_path: str | None, env_data: dict) -> Path:
    raw = args_path or env_data.get("DB_SQLITE_PATH") or "data/portfolio.db"
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def apply_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.close()


def make_sqlite_engine(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    event.listen(engine, "connect", apply_sqlite_pragmas)
    return engine


def report_orphaned_tables(mysql_table_names: set[str], orm_table_names: set[str]) -> None:
    """MySQL'de olup güncel ORM modelinde (Base.metadata) karşılığı olmayan tabloları bildirir.
    Bu tablolar SQLite'a taşınmaz; verileri scripts/backup_mysql.py yedeğinde eksiksiz durur."""
    orphaned = sorted(mysql_table_names - orm_table_names)
    if orphaned:
        print(
            f"\nUyarı: ORM modelinde karşılığı olmayan {len(orphaned)} tablo taşınmayacak "
            f"(scripts/backup_mysql.py yedeğinde saklı kalır): {', '.join(orphaned)}"
        )


def clear_target_tables(sqlite_conn, tables) -> None:
    """Hedef tablolardaki mevcut satırları FK-güvenli (child->parent) sırayla siler.
    Bu, scripti tekrar çalıştırılabilir (idempotent) yapar."""
    for table in reversed(tables):
        sqlite_conn.execute(delete(table))


def copy_table_rows(mysql_conn, sqlite_conn, source_table, target_table, chunk_size: int = 1000) -> tuple[int, int]:
    # Computed (generated) kolonlar hedefte otomatik hesaplanır, INSERT'e dahil edilmez.
    target_columns = {c.name for c in target_table.columns if c.computed is None}
    rows = mysql_conn.execute(select(source_table)).fetchall()
    row_dicts = [
        {k: v for k, v in dict(row._mapping).items() if k in target_columns}
        for row in rows
    ]

    for i in range(0, len(row_dicts), chunk_size):
        chunk = row_dicts[i:i + chunk_size]
        if chunk:
            sqlite_conn.execute(insert(target_table), chunk)

    target_rows = sqlite_conn.execute(select(target_table)).fetchall()
    return len(row_dicts), len(target_rows)


def checksum_critical_table(mysql_conn, sqlite_conn, source_table, target_table) -> tuple[bool, str]:
    """Kritik tablolar için birincil anahtar seti karşılaştırması (satır sayısı ötesinde doğrulama)."""
    pk_columns = list(target_table.primary_key.columns)
    if not pk_columns:
        return True, "birincil anahtar yok, atlandı"

    pk_name = pk_columns[0].name
    source_ids = {row[0] for row in mysql_conn.execute(select(source_table.c[pk_name])).fetchall()}
    target_ids = {row[0] for row in sqlite_conn.execute(select(target_table.c[pk_name])).fetchall()}

    if source_ids == target_ids:
        return True, f"{len(source_ids)} id eşleşti"

    missing_in_target = source_ids - target_ids
    extra_in_target = target_ids - source_ids
    detail = f"eksik={len(missing_in_target)} fazla={len(extra_in_target)}"
    return False, detail


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "MySQL verisini SQLite'a taşır (idempotent — tekrar çalıştırılabilir). "
            "Migration öncesi scripts/backup_mysql.py ile yedek alınmış olmalı (bkz. TRANSFORMATION_PLAN.md §9.1)."
        )
    )
    parser.add_argument("--env", default="", help="Ortam adı (örn. 'test' -> .env.test).")
    parser.add_argument(
        "--sqlite-path",
        default=None,
        help="Hedef SQLite dosya yolu (varsayılan: .env DB_SQLITE_PATH ya da data/portfolio.db)",
    )
    args = parser.parse_args()

    env_data = load_env_dict(args.env)
    mysql_url, host, database = make_mysql_url(env_data)
    sqlite_path = resolve_sqlite_path(args.sqlite_path, env_data)

    print("=== MYSQL -> SQLITE MIGRATION (migrate_mysql_to_sqlite.py) ===")
    print(f"Kaynak: {host} / {database}")
    print(f"Hedef:  {sqlite_path}")
    print("================================================================")

    mysql_engine = create_engine(mysql_url)
    mysql_metadata = MetaData()
    try:
        mysql_metadata.reflect(bind=mysql_engine)
    except Exception as e:
        print(f"Kaynak (MySQL) veritabanı yansıtılamadı: {e}")
        sys.exit(1)

    # Hedef şema, MySQL'den reflect edilen ham metadata ile DEĞİL, mevcut ORM (Base.metadata)
    # tanımıyla oluşturulur — MySQL'e özel COLLATE/charset gibi dialect farkları böylece
    # devreye girmeden SQLite'ta doğrudan uygulamanın kullanacağı şema kurulur.
    target_tables = Base.metadata.sorted_tables
    report_orphaned_tables(set(mysql_metadata.tables), {t.name for t in target_tables})

    sqlite_engine = make_sqlite_engine(sqlite_path)
    Base.metadata.create_all(bind=sqlite_engine, checkfirst=True)

    row_results: dict[str, tuple[int, int]] = {}
    checksum_results: dict[str, tuple[bool, str]] = {}

    with mysql_engine.connect() as mysql_conn, sqlite_engine.begin() as sqlite_conn:
        print("\nHedef tablolar temizleniyor (idempotent sıfırlama)...")
        clear_target_tables(sqlite_conn, target_tables)

        print("\nVeri taşınıyor...")
        for table in target_tables:
            source_table = mysql_metadata.tables.get(table.name)
            if source_table is None:
                print(f"  {table.name}: MySQL'de karşılığı yok, atlanıyor (yeni ORM tablosu, 0 satır).")
                row_results[table.name] = (0, 0)
                continue

            print(f"  {table.name} ...", end="", flush=True)
            source_count, target_count = copy_table_rows(mysql_conn, sqlite_conn, source_table, table)
            row_results[table.name] = (source_count, target_count)
            status = "OK" if source_count == target_count else "UYUŞMAZLIK"
            print(f" kaynak={source_count} hedef={target_count} [{status}]")

            if table.name in CRITICAL_TABLES:
                ok, detail = checksum_critical_table(mysql_conn, sqlite_conn, source_table, table)
                checksum_results[table.name] = (ok, detail)
                print(f"    checksum ({table.name}): {'OK' if ok else 'UYUŞMAZLIK'} — {detail}")

    mysql_engine.dispose()
    sqlite_engine.dispose()

    row_mismatches = [name for name, (s, t) in row_results.items() if s != t]
    checksum_mismatches = [name for name, (ok, _) in checksum_results.items() if not ok]

    total_source = sum(c[0] for c in row_results.values())
    total_target = sum(c[1] for c in row_results.values())
    print(f"\nToplam: kaynak={total_source} satır, hedef={total_target} satır.")

    if row_mismatches or checksum_mismatches:
        if row_mismatches:
            print(f"\nHATA: Satır sayısı uyuşmayan tablolar: {', '.join(row_mismatches)}")
        if checksum_mismatches:
            print(f"HATA: Checksum uyuşmayan kritik tablolar: {', '.join(checksum_mismatches)}")
        sys.exit(1)

    print("\nMigration doğrulandı: tüm tablolarda satır sayıları ve kritik tablo checksum'ları eşleşiyor.")


if __name__ == "__main__":
    main()
