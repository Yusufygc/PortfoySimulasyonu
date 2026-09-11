from __future__ import annotations

import sys
import json
import argparse
import decimal
import datetime
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, MetaData, select, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_env_dict(env_name: str = "") -> dict:
    filename = f".env.{env_name}" if env_name else ".env"
    env_path = ROOT / filename
    if not env_path.exists():
        print(f"Hata: {filename} dosyası bulunamadı!")
        sys.exit(1)
    return dotenv_values(env_path)


def make_db_url(env_data: dict) -> tuple[str, str, str]:
    host = env_data.get("DB_HOST")
    port = env_data.get("DB_PORT")
    user = env_data.get("DB_USER")
    password = env_data.get("DB_PASSWORD")
    database = env_data.get("DB_NAME")
    if not all([host, port, user, password, database]):
        print("Hata: Gerekli veritabanı bağlantı parametreleri eksik!")
        sys.exit(1)
    url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"
    return url, host, database


def json_default(value):
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    raise TypeError(f"Serileştirilemeyen tip: {type(value)}")


def fetch_create_statement(conn, table_name: str) -> str:
    result = conn.execute(text(f"SHOW CREATE TABLE `{table_name}`")).fetchone()
    return result[1]


def backup_table(conn, backup_dir: Path, table) -> int:
    table_name = table.name
    create_stmt = fetch_create_statement(conn, table_name)
    (backup_dir / f"{table_name}.schema.sql").write_text(create_stmt + ";\n", encoding="utf-8")

    rows = conn.execute(select(table)).fetchall()
    row_dicts = [dict(row._mapping) for row in rows]
    with open(backup_dir / f"{table_name}.data.json", "w", encoding="utf-8") as f:
        json.dump(row_dicts, f, default=json_default, ensure_ascii=False, indent=2)
    return len(row_dicts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "MySQL veritabanının tam yedeğini (şema + veri) backups/ altına alır. "
            "SQLite migration öncesi zorunlu adım (bkz. TRANSFORMATION_PLAN.md §9.1)."
        )
    )
    parser.add_argument("--env", default="", help="Ortam adı (örn. 'test' -> .env.test). Boşsa .env kullanılır.")
    parser.add_argument("--output-dir", default=None, help="Yedek kök dizini (varsayılan: backups/)")
    args = parser.parse_args()

    env_data = load_env_dict(args.env)
    db_url, host, database = make_db_url(env_data)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(args.output_dir) if args.output_dir else ROOT / "backups"
    backup_dir = output_root / f"mysql_backup_{database}_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    print("=== MYSQL YEDEKLEME (backup_mysql.py) ===")
    print(f"Kaynak: {host} / {database}")
    print(f"Hedef dizin: {backup_dir}")
    print("==========================================")

    engine = create_engine(db_url)
    metadata = MetaData()
    try:
        metadata.reflect(bind=engine)
    except Exception as e:
        print(f"Veritabanı yansıtılamadı: {e}")
        sys.exit(1)

    manifest = {
        "source_host": host,
        "source_database": database,
        "created_at": timestamp,
        "tables": {},
    }

    with engine.connect() as conn:
        for table in metadata.sorted_tables:
            print(f"Yedekleniyor: {table.name} ...", end="", flush=True)
            row_count = backup_table(conn, backup_dir, table)
            manifest["tables"][table.name] = row_count
            print(f" {row_count} satır.")

    with open(backup_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total_rows = sum(manifest["tables"].values())
    print(f"\nYedekleme tamamlandı: {len(manifest['tables'])} tablo, {total_rows} satır.")
    print(f"Manifest: {backup_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
