import sys
import os
import yfinance as yf
from datetime import date, timedelta, datetime
import pandas as pd

# Proje ana dizinini Python yoluna ekle (Modüllerin bulunabilmesi için)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

# Gerekli modülleri import et
from config.settings_loader import load_settings
from src.infrastructure.db.mysql_connection import MySQLConnectionProvider
from src.infrastructure.db.stock_repository import MySQLStockRepository
from src.infrastructure.db.price_repository import MySQLPriceRepository
from src.domain.models.daily_price import DailyPrice

def backfill_process(start_date: date, end_date: date):
    """
    Belirtilen tarih aralığı için (end_date hariçtir, yfinance mantığı) verileri çeker ve kaydeder.
    """
    print(f"\n--- Veri Çekme İşlemi Başlatılıyor ---")
    print(f"Hedef: {start_date} ile {end_date - timedelta(days=1)} arası")

    # 1. Bağlantı
    try:
        config = load_settings()
        db_provider = MySQLConnectionProvider(config)
        stock_repo = MySQLStockRepository(db_provider)
        price_repo = MySQLPriceRepository(db_provider)
        print("Veritabanı bağlantısı sağlandı.")
    except Exception as e:
        print(f"HATA: Veritabanı bağlantısı kurulamadı: {e}")
        return

    # 2. Hisseleri Çek
    stocks = stock_repo.get_all_stocks()
    if not stocks:
        print("Veritabanında kayıtlı hisse yok.")
        return

    tickers = [s.ticker for s in stocks]
    stock_map = {s.ticker: s.id for s in stocks}
    print(f"İşlenecek Hisseler ({len(tickers)}): {', '.join(tickers)}")

    # 3. YFinance İndirme
    try:
        print("Yahoo Finance'den veri indiriliyor...")
        # auto_adjust=False: Bölünme/Temettü olmadan saf kapanış fiyatını alır (Tercihe bağlı)
        df = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=False, progress=True)
    except Exception as e:
        print(f"HATA: İndirme başarısız: {e}")
        return

    if df.empty:
        print("Bu tarih aralığı için veri bulunamadı.")
        return

    # 4. Veriyi İşleme
    prices_to_save = []
    is_multi_index = isinstance(df.columns, pd.MultiIndex)

    print("Veriler işleniyor...")
    for ticker in tickers:
        stock_id = stock_map.get(ticker)
        if not stock_id: continue

        try:
            # Tek hisse varsa DataFrame yapısı düzdür, çoklu hisse varsa MultiIndex'tir
            if is_multi_index:
                if ticker not in df.columns.levels[0]:
                    print(f"- {ticker}: Veri yok.")
                    continue
                stock_data = df[ticker]
            else:
                # Eğer tek bir hisse indirdiysek
                if len(tickers) == 1:
                    stock_data = df
                else:
                    continue

            for timestamp, row in stock_data.iterrows():
                # 'Close' sütununu al
                close_val = row.get('Close')
                
                # Bazen yfinance Series dönebilir, float'a çevirelim
                if isinstance(close_val, pd.Series):
                    close_val = close_val.iloc[0]
                
                # NaN veya boş veri kontrolü
                if pd.isna(close_val):
                    continue

                daily_price = DailyPrice(
                    id=None,
                    stock_id=stock_id,
                    price_date=timestamp.date(),
                    close_price=float(close_val)
                )
                prices_to_save.append(daily_price)

        except Exception as e:
            print(f"Hata ({ticker}): {e}")
            continue

    # 5. Kaydetme
    if prices_to_save:
        try:
            count = price_repo.upsert_daily_prices_bulk(prices_to_save)
            print(f"\n✅ BAŞARILI: {len(prices_to_save)} adet fiyat verisi veritabanına işlendi.")
        except Exception as e:
            print(f"HATA: Kayıt sırasında sorun: {e}")
    else:
        print("\n⚠️ Kaydedilecek anlamlı veri bulunamadı.")

def get_date_input(prompt: str) -> date:
    """Kullanıcıdan YYYY-MM-DD formatında tarih alır."""
    while True:
        d_str = input(prompt + " (YYYY-MM-DD): ").strip()
        try:
            return datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Hatalı format! Lütfen YYYY-AA-GG şeklinde giriniz. (Örn: 2025-12-04)")

def main_interactive():
    print("#############################################")
    print("#   PORTFÖY SİMÜLASYONU - VERİ TAMAMLAMA    #")
    print("#############################################")
    print("1. Tek Bir Gün İçin Veri Çek")
    print("2. Belirli Bir Tarih Aralığı İçin Veri Çek")
    print("3. Çıkış")
    
    choice = input("\nSeçiminiz (1/2/3): ").strip()

    if choice == '1':
        print("\n--- Tek Gün Modu ---")
        target_date = get_date_input("Hangi günün kapanış verisini istiyorsunuz?")
        
        # yfinance'da 'end' tarihi dahil edilmez, bu yüzden +1 gün ekliyoruz
        # Örnek: Start 2025-12-04, End 2025-12-05 -> Sadece 04'ünü getirir.
        start_date = target_date
        end_date = target_date + timedelta(days=1)
        
        backfill_process(start_date, end_date)

    elif choice == '2':
        print("\n--- Tarih Aralığı Modu ---")
        start_date = get_date_input("Başlangıç Tarihi")
        end_input = get_date_input("Bitiş Tarihi (Bu gün DAHİL)")
        
        if start_date > end_input:
            print("❌ Hata: Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return

        # Bitiş tarihini dahil etmek için +1 gün ekle
        end_date = end_input + timedelta(days=1)
        
        backfill_process(start_date, end_date)

    elif choice == '3':
        print("Çıkış yapılıyor.")
        return
    else:
        print("Geçersiz seçim.")

if __name__ == "__main__":
    main_interactive()