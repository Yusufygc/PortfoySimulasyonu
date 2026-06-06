from __future__ import annotations

import sys
import argparse
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import create_engine, MetaData, select, insert, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_env_dict(env_name: str) -> dict:
    filename = f".env.{env_name}" if env_name else ".env"
    env_path = ROOT / filename
    if not env_path.exists():
        print(f"Hata: {filename} dosyası bulunamadı!")
        sys.exit(1)
    return dotenv_values(env_path)


def make_db_url(env_data: dict) -> str:
    host = env_data.get("DB_HOST")
    port = env_data.get("DB_PORT")
    user = env_data.get("DB_USER")
    password = env_data.get("DB_PASSWORD")
    database = env_data.get("DB_NAME")
    if not all([host, port, user, password, database]):
        print("Hata: Gerekli veritabanı bağlantı parametreleri eksik!")
        sys.exit(1)
    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{database}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Canlı veritabanını test veritabanına kopyalar.")
    parser.add_argument("--force", action="store_true", help="Kullanıcı onayını sormadan kopyalar.")
    args = parser.parse_args()

    # Load configs
    prod_env = load_env_dict("")
    test_env = load_env_dict("test")

    prod_db = prod_env.get("DB_NAME")
    test_db = test_env.get("DB_NAME")
    prod_host = prod_env.get("DB_HOST")
    test_host = test_env.get("DB_HOST")

    # Safety checks
    if prod_db == test_db and prod_host == test_host:
        print("KRİTİK HATA: Üretim (Prod) ve Test veritabanı isimleri ve hostları tamamen aynı!")
        print("Canlı veriyi ezmemek için işlem durduruldu.")
        sys.exit(1)

    print("=== PORTFÖY SİMÜLASYONU VERİTABANI KOPYALAMA ===")
    print(f"KAYNAK (Üretim): {prod_host} / {prod_db}")
    print(f"HEDEF (Test):    {test_host} / {test_db}")
    print("================================================")

    if not args.force:
        confirm = input(f"DİKKAT: Test veritabanındaki ({test_db}) tüm veriler silinecek! Devam etmek istiyor musunuz? [y/N]: ")
        if confirm.lower() not in ("y", "yes", "evet"):
            print("İşlem kullanıcı tarafından iptal edildi.")
            sys.exit(0)

    prod_url = make_db_url(prod_env)
    test_url = make_db_url(test_env)

    prod_engine = create_engine(prod_url)
    test_engine = create_engine(test_url)

    print("Bağlantılar kuruluyor...")

    prod_metadata = MetaData()
    try:
        prod_metadata.reflect(bind=prod_engine)
    except Exception as e:
        print(f"Kaynak veritabanı yansıtılamadı: {e}")
        sys.exit(1)

    print(f"Kaynak veritabanından {len(prod_metadata.tables)} tablo okundu.")

    with test_engine.begin() as test_conn:
        # Turn off foreign keys
        test_conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

        # Reflect and drop existing target tables
        print("Hedef veritabanındaki eski tablolar siliniyor...")
        test_metadata = MetaData()
        test_metadata.reflect(bind=test_conn)
        test_metadata.drop_all(bind=test_conn)

        # Recreate target tables from source metadata
        print("Tablo şemaları oluşturuluyor...")
        prod_metadata.create_all(bind=test_conn)

        with prod_engine.connect() as prod_conn:
            # Copy data table by table
            for table in prod_metadata.sorted_tables:
                table_name = table.name

                # Fetch all data from source table
                rows = prod_conn.execute(select(table)).fetchall()
                row_count = len(rows)
                print(f"Kopyalanıyor: {table_name} ({row_count} satır)...", end="", flush=True)

                if row_count > 0:
                    # Veritabanında otomatik hesaplanan (computed) kolonları filtrele
                    computed_cols = {col.name for col in table.columns if col.computed is not None}
                    
                    insert_data = []
                    for row in rows:
                        row_dict = dict(row._mapping)
                        for col_name in computed_cols:
                            row_dict.pop(col_name, None)
                        insert_data.append(row_dict)

                    chunk_size = 1000
                    for i in range(0, row_count, chunk_size):
                        chunk = insert_data[i:i + chunk_size]
                        test_conn.execute(insert(table), chunk)
                print(" Tamamlandı.")

        # Re-enable foreign keys
        test_conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

    print("\nVeritabanı başarıyla kopyalandı!")


if __name__ == "__main__":
    main()
