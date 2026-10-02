"""
sync_bist_to_duckdb.py — Tüm BIST hisselerinin ilk günden bugüne geçmişini DuckDB'ye senkronize eder.

Kullanım:
    python scripts/sync_bist_to_duckdb.py                  # Tüm BIST hisselerini indirir
    python scripts/sync_bist_to_duckdb.py --limit 30       # İlk 30 hisseyi indirir (test için)
    python scripts/sync_bist_to_duckdb.py --tickers THYAO,BIMAS,ASELS,EREGL
"""
import argparse
import os
import sys
import time

# Proje kök dizinini ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.application.services.market_data.bist_bulk_downloader import BistBulkDownloader


def main():
    parser = argparse.ArgumentParser(description="Tüm BIST hisse geçmişini DuckDB'ye aktarır.")
    parser.add_argument("--workers", type=int, default=5, help="Paralel worker iş parçacığı sayısı (varsayılan: 5)")
    parser.add_argument("--limit", type=int, default=None, help="İndirilecek maksimum hisse sayısı")
    parser.add_argument("--tickers", type=str, default=None, help="Virgülle ayrılmış belirli hisseler (ör: THYAO,BIMAS)")
    parser.add_argument("--db-path", type=str, default=None, help="DuckDB dosya yolu (varsayılan: data/market_history.duckdb)")
    args = parser.parse_args()

    downloader = BistBulkDownloader(db_path=args.db_path, max_workers=args.workers)

    print("=" * 70)
    print(" BIST GEÇMİŞ VERİ SENKRONİZASYONU (DUCKDB OLAP KATMANI)")
    print("=" * 70)

    if args.tickers:
        target_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
        print(f"Belirtilen hisseler: {target_tickers}")
    else:
        print("TradingView Scanner API üzerinden tüm BIST hisse listesi taranıyor...")
        target_tickers = downloader.fetch_all_bist_tickers()
        print(f"Toplam tespit edilen BIST hissesi: {len(target_tickers)}")
        if args.limit:
            target_tickers = target_tickers[:args.limit]
            print(f"--limit parametresi uygulandı: İlk {len(target_tickers)} hisse indirilecek.")

    print(f"\nİndirme işlemi başlatılıyor ({args.workers} paralel iş parçacığı)...")
    t0 = time.time()
    total_saved_rows = 0

    def on_progress(completed, total, ticker, rows):
        nonlocal total_saved_rows
        total_saved_rows += rows
        pct = (completed / total) * 100
        print(f"[{completed:3d}/{total:3d}] (%{pct:5.1f}) {ticker:<6} -> {rows:,} bar kaydedildi")

    results = downloader.sync_all(tickers=target_tickers, progress_cb=on_progress)
    elapsed = time.time() - t0

    db_size_mb = os.path.getsize(args.db_path) / (1024 * 1024) if os.path.exists(args.db_path) else 0

    print("\n" + "=" * 70)
    print(" SENKRONİZASYON TAMAMLANDI")
    print("=" * 70)
    print(f"  Başarılı Hisse Sayısı : {len(results):,} / {len(target_tickers):,}")
    print(f"  Toplam Eklenen Bar     : {total_saved_rows:,}")
    print(f"  Geçen Süre             : {elapsed:.2f} saniye")
    print(f"  DuckDB Dosya Boyutu    : {db_size_mb:.2f} MB ({args.db_path})")
    print("=" * 70)


if __name__ == "__main__":
    main()
