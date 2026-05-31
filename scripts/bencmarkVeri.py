import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Proje kök dizinini sys.path'e ekliyoruz (Clean Architecture importları için)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# .env dosyasından API anahtarları ve ayarları yüklüyoruz
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from src.application.services.analysis.benchmark_service import AnalysisBenchmarkService
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient
from src.infrastructure.market_data.evds_client import EvdsClient

def format_decimal(val):
    return f"{val:.4f}".rstrip("0").rstrip(".")

def main():
    print("=" * 80)
    print("PORTFÖY SİMÜLASYONU — BENCHMARK VERİ CANLI TEST SCRIPT'İ")
    print("=" * 80)
    
    # İstemcilerin başlatılması
    print("[1/3] Servis ve API istemcileri başlatılıyor...")
    yfinance_client = YFinanceMarketDataClient(timeout=15)
    evds_client = EvdsClient(timeout=15)
    service = AnalysisBenchmarkService(market_data_client=yfinance_client, evds_client=evds_client)
    
    # Tarih aralığının belirlenmesi (Son 30 gün)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    print(f"[2/3] Tarih aralığı: {start_date} - {end_date} (Son 30 gün)")
    
    codes = ["bist100", "gold", "silver", "usd", "euro", "deposit", "cpi"]
    print(f"Çekilecek benchmark verileri: {', '.join(codes)}")
    print("-" * 80)
    
    # Verilerin çekilmesi
    print("[3/3] Veriler API'lerden çekiliyor (Lütfen bekleyin)...")
    results, warnings = service.build_benchmark_series(start_date, end_date, codes)
    
    print("\n" + "=" * 80)
    print("ÇEKİLEN VERİ ÖZETLERİ")
    print("=" * 80)
    
    # Sonuçların gösterilmesi
    for series in results:
        points_count = len(series.points)
        print(f"\n* Kod: {series.code:<8} | Baslik: {series.label:<15} | Veri Noktasi: {points_count} gun")
        if points_count > 0:
            sorted_points = sorted(series.points.items())
            first_date, first_val = sorted_points[0]
            last_date, last_val = sorted_points[-1]
            print(f"  Ilk Tarih: {first_date} -> Fiyat/Deger: {format_decimal(first_val)}")
            print(f"  Son Tarih: {last_date} -> Fiyat/Deger: {format_decimal(last_val)}")
            
            # Son 5 günün verisini detaylı gösterelim
            print("  Son 5 Gun Detayi:")
            for dt, val in sorted_points[-5:]:
                print(f"    {dt} -> {format_decimal(val)}")
        else:
            print("  [UYARI] Veri cekilemedi.")
            
    # Eğer uyarılar varsa ekrana yazdıralım
    if warnings:
        print("\n" + "=" * 80)
        print("UYARILAR VE BILGILENDIRMELER")
        print("=" * 80)
        for idx, warning in enumerate(warnings, 1):
            # Not uyarısı dışındakileri belirgin yazalım
            if "Not:" in warning:
                print(f"  [Bilgi] {warning}")
            else:
                print(f"  [Hata]  {warning}")
                
    print("\n" + "=" * 80)
    print("Test Tamamlandı!")
    print("=" * 80)

if __name__ == "__main__":
    main()
