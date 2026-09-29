"""
Sync script: backups/mysql/portfoysim.sql içindeki eksik kayıtları data/portfolio.db'ye aktarır.
"""
import re
import sqlite3
import time

def sync_backup_to_sqlite():
    start_time = time.time()
    conn = sqlite3.connect('data/portfolio.db')
    cursor = conn.cursor()

    # Performans ayarları
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")
    cursor.execute("PRAGMA foreign_keys = OFF;")

    print("Yedek SQL dosyası taranıyor: backups/mysql/portfoysim.sql ...")

    tables_to_sync = [
        "stocks", "kap_companies", "kap_shareholder_snapshots", 
        "kap_shareholder_rows", "daily_prices", "latest_prices", 
        "golden_cross_events", "trend_signals"
    ]

    inserted_counts = {t: 0 for t in tables_to_sync}

    with open('backups/mysql/portfoysim.sql', 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.startswith("INSERT INTO "):
                continue

            for table in tables_to_sync:
                pattern = f"INSERT INTO `{table}` VALUES "
                if line.startswith(pattern):
                    # Replace with INSERT OR IGNORE
                    sql = line.replace(f"INSERT INTO `{table}`", f"INSERT OR IGNORE INTO `{table}`")
                    # Clean MySQL specifics if any
                    try:
                        cursor.execute(sql)
                        inserted_counts[table] += cursor.rowcount
                    except Exception as e:
                        print(f"Hata ({table}): {e}")
                    break

    conn.commit()
    conn.close()
    
    elapsed = time.time() - start_time
    print(f"\nSenkronizasyon tamamlandi ({elapsed:.2f} sn)!")
    for t, cnt in inserted_counts.items():
        if cnt > 0:
            print(f"  {t}: {cnt} yeni kayit eklendi.")

if __name__ == "__main__":
    sync_backup_to_sqlite()
