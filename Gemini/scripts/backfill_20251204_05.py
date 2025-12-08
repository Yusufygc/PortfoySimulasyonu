"""
scripts/backfill_20251204_05_improved.py

Hisse Bazlı Gün Sonu Değerlendirme Scripti
- Veritabanındaki TÜM işlemleri analiz eder
- Her gün için o güne kadar olan durumu hesaplar
- İki günü karşılaştırır
"""

import os
import sys
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import mysql.connector
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

# ------------------ KONFİG ------------------ #

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "portfoySim"),
}

EXCEL_PATH = os.getenv("PORTFOY_EXCEL_PATH", "portfoy_takip.xlsx")

# TARGET_DATES'i otomatik tespit etmek için None bırakabiliriz
# veya manuel olarak belirtebiliriz
TARGET_DATES = None  # Otomatik tespit için None
# TARGET_DATES = [date(2025, 12, 4), date(2025, 12, 5)]  # Manuel

# ------------------ DB YARDIMCI ------------------ #

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all_trades() -> List[dict]:
    """Tüm işlemleri getirir"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            id, stock_id, trade_date, trade_time,
            side, quantity, price
        FROM trades
        ORDER BY trade_date, trade_time, id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def fetch_all_stocks() -> Dict[int, str]:
    """stocks tablosundan id -> ticker map'i döner"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, ticker FROM stocks")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {row["id"]: row["ticker"] for row in rows}


# ------------------ TOPLU FİYAT ÇEKİMİ ------------------ #

def fetch_prices_bulk(tickers: List[str], target_date: date) -> Dict[str, Optional[Decimal]]:
    """Tüm hisseler için tek seferde fiyat çeker"""
    if not tickers:
        return {}
    
    prices = {}
    start = target_date
    end = target_date + timedelta(days=1)
    
    print(f"\n[INFO] {len(tickers)} hisse için toplu fiyat çekiliyor: {target_date}")
    
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start, end=end, auto_adjust=False)
            
            if hist is not None and not hist.empty and "Close" in hist:
                close_series = hist["Close"].dropna()
                if not close_series.empty:
                    last_price = close_series.iloc[-1]
                    prices[ticker] = Decimal(str(float(last_price)))
                    print(f"  ✓ {ticker}: {prices[ticker]:.4f} TL")
                else:
                    prices[ticker] = None
                    print(f"  ✗ {ticker}: Close verisi yok")
            else:
                prices[ticker] = None
                print(f"  ✗ {ticker}: History boş")
        except Exception as e:
            print(f"  ✗ {ticker}: Hata - {e}")
            prices[ticker] = None
    
    return prices


# ------------------ POZİSYON YÖNETİMİ ------------------ #

class Position:
    """Hisse pozisyonu yönetimi"""
    def __init__(self):
        self.qty = Decimal("0")
        self.total_cost = Decimal("0")
    
    @property
    def avg_cost(self) -> Decimal:
        """Ortalama maliyet"""
        return (self.total_cost / self.qty) if self.qty != 0 else Decimal("0")
    
    def buy(self, quantity: int, price: Decimal):
        """Alış işlemi"""
        qty_dec = Decimal(quantity)
        self.qty += qty_dec
        self.total_cost += qty_dec * price
    
    def sell(self, quantity: int):
        """Satış işlemi"""
        sell_qty = min(Decimal(quantity), self.qty)
        if self.qty != 0:
            self.total_cost -= self.avg_cost * sell_qty
        self.qty -= sell_qty
        if self.qty == 0:
            self.total_cost = Decimal("0")
    
    def copy(self):
        """Pozisyon kopyası"""
        new_pos = Position()
        new_pos.qty = self.qty
        new_pos.total_cost = self.total_cost
        return new_pos
    
    def calculate_metrics(self, current_price: Optional[Decimal], 
                         prev_price: Optional[Decimal] = None) -> dict:
        """Hisse için tüm metrikleri hesaplar"""
        if current_price is None:
            return {
                "position_value": None,
                "unrealized_pnl_tl": None,
                "unrealized_pnl_pct": None,
                "daily_price_change_pct": None,
                "cost_basis": self.avg_cost * self.qty if self.qty > 0 else Decimal("0")
            }
        
        if self.qty == 0:
            return {
                "position_value": Decimal("0"),
                "unrealized_pnl_tl": Decimal("0"),
                "unrealized_pnl_pct": Decimal("0"),
                "daily_price_change_pct": None,
                "cost_basis": Decimal("0")
            }
        
        position_value = self.qty * current_price
        cost_basis = self.avg_cost * self.qty
        unrealized_pnl_tl = (current_price - self.avg_cost) * self.qty
        unrealized_pnl_pct = (unrealized_pnl_tl / cost_basis) if cost_basis != 0 else None
        
        daily_change_pct = None
        if prev_price is not None and prev_price != 0:
            daily_change_pct = (current_price / prev_price) - Decimal("1")
        
        return {
            "position_value": position_value,
            "unrealized_pnl_tl": unrealized_pnl_tl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "daily_price_change_pct": daily_change_pct,
            "cost_basis": cost_basis
        }


# ------------------ ANA İŞLEM MOTORU ------------------ #

def build_stock_level_history(
    trades: List[dict],
    ticker_map: Dict[int, str],
    dates: List[date],
) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Her tarih için o tarihe KADAR olan tüm işlemleri işleyerek
    o tarihteki durumu hesaplar
    """
    
    def sort_key(row):
        trade_time = row.get("trade_time") or dt_time.min
        return (row["trade_date"], trade_time, row["id"])
    
    trades = sorted(trades, key=sort_key)
    
    # trade_date'leri datetime.date'e normalize et
    for t in trades:
        if isinstance(t["trade_date"], datetime):
            t["trade_date"] = t["trade_date"].date()
    
    # Her işleme stock_id bazında bakalım
    stocks_with_trades = set(t["stock_id"] for t in trades)
    print(f"\n[INFO] İşlem yapılan hisseler: {len(stocks_with_trades)}")
    for sid in stocks_with_trades:
        ticker = ticker_map.get(sid, f"ID_{sid}")
        trade_count = sum(1 for t in trades if t["stock_id"] == sid)
        trades_for_stock = [t for t in trades if t["stock_id"] == sid]
        earliest = min(t["trade_date"] for t in trades_for_stock)
        latest = max(t["trade_date"] for t in trades_for_stock)
        print(f"  - {ticker} (ID:{sid}): {trade_count} işlem [{earliest} ~ {latest}]")
    
    summary_rows: List[dict] = []
    detail_rows: List[dict] = []
    stock_summary_rows: List[dict] = []
    
    # Bir önceki günün fiyatlarını ve portföy değerini sakla
    prev_prices: Dict[int, Decimal] = {}
    prev_portfolio_value: Optional[Decimal] = None
    base_portfolio_value: Optional[Decimal] = None
    
    for current_date in sorted(dates):
        print(f"\n{'='*70}")
        print(f"📅 İŞLENEN TARİH: {current_date.strftime('%d/%m/%Y (%A)')}")
        print(f"{'='*70}")
        
        # 1) Bu tarihe KADAR olan TÜM işlemleri işle
        positions: Dict[int, Position] = defaultdict(Position)
        
        processed_trades = 0
        for t in trades:
            if t["trade_date"] <= current_date:
                stock_id = t["stock_id"]
                qty = int(t["quantity"])
                price = Decimal(str(t["price"]))
                side = t["side"]
                
                if side == "BUY":
                    positions[stock_id].buy(qty, price)
                elif side == "SELL":
                    positions[stock_id].sell(qty)
                
                processed_trades += 1
        
        print(f"✓ {processed_trades} işlem işlendi ({current_date} tarihine kadar)")
        
        # 2) Aktif pozisyonları tespit et (qty > 0 olanlar)
        active_positions = {sid: pos for sid, pos in positions.items() if pos.qty > 0}
        
        if not active_positions:
            print(f"⚠ {current_date} tarihinde aktif pozisyon YOK (tüm hisseler satılmış olabilir)")
            # Boş gün için özet ekle
            summary_rows.append({
                "Tarih": current_date,
                "Portföy Değeri": Decimal("0"),
                "Günlük Getiri %": None,
                "Toplam Getiri %": None,
                "Günlük K/Z": None,
                "Toplam K/Z": None,
                "Aktif Hisse Sayısı": 0,
                "Durum": "Pozisyon Yok",
            })
            continue
        
        print(f"\n📊 Aktif Pozisyonlar ({len(active_positions)} hisse):")
        for sid, pos in active_positions.items():
            ticker = ticker_map.get(sid, f"ID_{sid}")
            print(f"  - {ticker}: {int(pos.qty)} lot @ {pos.avg_cost:.4f} TL ort. maliyet")
        
        # 3) Toplu fiyat çek
        tickers_to_fetch = [ticker_map.get(sid, f"ID_{sid}") for sid in active_positions.keys()]
        prices = fetch_prices_bulk(tickers_to_fetch, current_date)
        
        # 4) Her hisse için metrikleri hesapla
        portfolio_value = Decimal("0")
        stock_details = []
        price_found_count = 0
        
        for stock_id, pos in active_positions.items():
            ticker = ticker_map.get(stock_id, f"ID_{stock_id}")
            current_price = prices.get(ticker)
            prev_price = prev_prices.get(stock_id)
            
            if current_price is not None:
                price_found_count += 1
            
            metrics = pos.calculate_metrics(current_price, prev_price)
            
            if metrics["position_value"] is not None:
                portfolio_value += metrics["position_value"]
            
            stock_details.append({
                "stock_id": stock_id,
                "ticker": ticker,
                "qty": int(pos.qty),
                "avg_cost": pos.avg_cost,
                "current_price": current_price,
                **metrics
            })
            
            # Bir sonraki gün için fiyatı sakla
            if current_price is not None:
                prev_prices[stock_id] = current_price
        
        print(f"\n💰 Fiyat Durumu: {price_found_count}/{len(active_positions)} hisse için fiyat bulundu")
        
        # 5) Portföy değeri yoksa önceki günün değerini kullan
        portfolio_value_for_calc = portfolio_value if portfolio_value > 0 else prev_portfolio_value
        
        # 6) Portföy ağırlıklarını hesapla ve detay satırlarını oluştur
        for detail in stock_details:
            if portfolio_value > 0 and detail["position_value"] is not None:
                detail["weight_pct"] = detail["position_value"] / portfolio_value
            else:
                detail["weight_pct"] = None
            
            detail_rows.append({
                "Tarih": current_date,
                "Ticker": detail["ticker"],
                "Stock ID": detail["stock_id"],
                "Lot": detail["qty"],
                "Ortalama Maliyet": detail["avg_cost"],
                "Güncel Fiyat": detail["current_price"],
                "Pozisyon Değeri": detail["position_value"],
                "Maliyet Esası": detail["cost_basis"],
                "Günlük Fiyat Değişim %": detail["daily_price_change_pct"],
                "Gerç. Olmayan K/Z (TL)": detail["unrealized_pnl_tl"],
                "Gerç. Olmayan K/Z %": detail["unrealized_pnl_pct"],
                "Portföy Ağırlığı %": detail["weight_pct"],
            })
        
        # 7) Portföy seviyesi metrikleri
        if base_portfolio_value is None and portfolio_value_for_calc is not None:
            base_portfolio_value = portfolio_value_for_calc
        
        daily_pnl = None
        daily_ret_pct = None
        cumulative_pnl = None
        cumulative_ret_pct = None
        
        if portfolio_value_for_calc is not None:
            if prev_portfolio_value is not None and prev_portfolio_value != 0:
                daily_pnl = portfolio_value_for_calc - prev_portfolio_value
                daily_ret_pct = daily_pnl / prev_portfolio_value
            
            if base_portfolio_value is not None and base_portfolio_value != 0:
                cumulative_pnl = portfolio_value_for_calc - base_portfolio_value
                cumulative_ret_pct = cumulative_pnl / base_portfolio_value
        
        # Durum belirleme
        if price_found_count == len(active_positions):
            status = "Normal"
        elif price_found_count == 0:
            if current_date.weekday() >= 5:
                status = "Hafta Sonu - Fiyat Yok"
            else:
                status = "Fiyat Verisi Yok"
        else:
            status = f"Kısmi Veri ({price_found_count}/{len(active_positions)})"
        
        summary_rows.append({
            "Tarih": current_date,
            "Portföy Değeri": portfolio_value_for_calc,
            "Günlük Getiri %": daily_ret_pct,
            "Toplam Getiri %": cumulative_ret_pct,
            "Günlük K/Z": daily_pnl,
            "Toplam K/Z": cumulative_pnl,
            "Aktif Hisse Sayısı": len(active_positions),
            "Durum": status,
        })
        
        if portfolio_value_for_calc is not None:
            prev_portfolio_value = portfolio_value_for_calc
        
        print(f"\n📈 Portföy Özeti:")
        print(f"  Toplam Değer: {portfolio_value_for_calc:,.2f} TL" if portfolio_value_for_calc else "  Toplam Değer: Hesaplanamadı")
        if daily_ret_pct:
            print(f"  Günlük Getiri: {daily_ret_pct*100:+.2f}%")
        if cumulative_ret_pct:
            print(f"  Toplam Getiri: {cumulative_ret_pct*100:+.2f}%")
    
    # 8) Hisse bazında karşılaştırmalı özet
    print(f"\n{'='*70}")
    print("📊 HİSSE BAZINDA KARŞILAŞTIRMALI ÖZET")
    print(f"{'='*70}")
    
    # İki günü karşılaştır
    if len(dates) >= 2:
        date1, date2 = dates[0], dates[1]
        details_day1 = [d for d in detail_rows if d["Tarih"] == date1]
        details_day2 = [d for d in detail_rows if d["Tarih"] == date2]
        
        print(f"\n🔄 {date1.strftime('%d/%m/%Y')} → {date2.strftime('%d/%m/%Y')} Karşılaştırması:\n")
        
        # Ticker bazında grupla
        tickers_all = set(d["Ticker"] for d in details_day1 + details_day2)
        
        for ticker in sorted(tickers_all):
            day1_data = next((d for d in details_day1 if d["Ticker"] == ticker), None)
            day2_data = next((d for d in details_day2 if d["Ticker"] == ticker), None)
            
            print(f"  {ticker}:")
            if day1_data and day2_data:
                price1 = day1_data["Güncel Fiyat"]
                price2 = day2_data["Güncel Fiyat"]
                if price1 and price2:
                    change = ((price2/price1) - 1) * 100
                    print(f"    Fiyat: {price1:.4f} → {price2:.4f} TL ({change:+.2f}%)")
                    
                    pnl1 = day1_data["Gerç. Olmayan K/Z (TL)"]
                    pnl2 = day2_data["Gerç. Olmayan K/Z (TL)"]
                    if pnl1 is not None and pnl2 is not None:
                        pnl_change = pnl2 - pnl1
                        print(f"    K/Z: {pnl1:,.2f} → {pnl2:,.2f} TL ({pnl_change:+,.2f} TL)")
            elif day1_data:
                print(f"    {date2.strftime('%d/%m/%Y')} tarihinde POZİSYON YOK (satılmış)")
            elif day2_data:
                print(f"    {date1.strftime('%d/%m/%Y')} tarihinde POZİSYON YOK (sonradan alınmış)")
            print()
    
    # 9) Her hisse için son durum özeti
    for stock_id in stocks_with_trades:
        ticker = ticker_map.get(stock_id, f"ID_{stock_id}")
        stock_details_list = [d for d in detail_rows if d["Stock ID"] == stock_id]
        
        if not stock_details_list:
            continue
        
        latest = stock_details_list[-1]
        
        stock_summary_rows.append({
            "Ticker": ticker,
            "Stock ID": stock_id,
            "Son Lot": latest["Lot"],
            "Ort. Maliyet": latest["Ortalama Maliyet"],
            "Son Fiyat": latest["Güncel Fiyat"],
            "Son Pozisyon Değeri": latest["Pozisyon Değeri"],
            "Toplam Gerç.Olmayan K/Z (TL)": latest["Gerç. Olmayan K/Z (TL)"],
            "Toplam Gerç.Olmayan K/Z %": latest["Gerç. Olmayan K/Z %"],
            "Gün Sayısı": len(stock_details_list),
        })
    
    return summary_rows, detail_rows, stock_summary_rows


# ------------------ EXCEL YAZMA ------------------ #

def to_float(x):
    """Decimal/None değerleri float'a çevir"""
    if x is None:
        return None
    if isinstance(x, Decimal):
        return float(x)
    return x


def update_excel_improved(
    summary_rows: List[dict], 
    detail_rows: List[dict],
    stock_summary_rows: List[dict],
    path: str
):
    """
    Geliştirilmiş Excel çıktısı
    
    EXCEL YAPISI:
    - Sheet 1 (StockDetails): Her satır = 1 hisse x 1 gün (ANA SHEET)
    - Sheet 2 (PortfolioSummary): Her satır = 1 gün (özet)
    - Sheet 3 (StockSummary): Her satır = 1 hisse (genel özet)
    """
    
    # Excel dosyası açık mı kontrol et
    try:
        test_file = open(path, 'a')
        test_file.close()
    except PermissionError:
        print(f"\n{'='*70}")
        print("❌ HATA: Excel dosyası açık!")
        print(f"{'='*70}")
        print(f"Lütfen '{path}' dosyasını kapatın ve tekrar deneyin.")
        print()
        sys.exit(1)
    
    # DataFrame'leri oluştur - date'leri pd.Timestamp'e çevir
    def prepare_row(r):
        result = {}
        for k, v in r.items():
            if k == "Tarih" and isinstance(v, date):
                result[k] = pd.Timestamp(v)
            else:
                result[k] = to_float(v)
        return result
    
    # ANA SHEET: HER SATIR = 1 HİSSE x 1 GÜN
    df_details = pd.DataFrame([prepare_row(r) for r in detail_rows])
    
    # ÖZET SHEET 1: GÜN BAZINDA TOPLAM PORTFÖY
    df_summary = pd.DataFrame([prepare_row(r) for r in summary_rows])
    
    # ÖZET SHEET 2: HİSSE BAZINDA SON DURUM
    df_stock_summary = pd.DataFrame([{k: to_float(v) for k, v in r.items()} 
                                      for r in stock_summary_rows])
    
    # Mevcut verileri oku (varsa)
    existing_dfs = {}
    if os.path.exists(path):
        try:
            with pd.ExcelFile(path, engine='openpyxl') as xls:
                for sheet_name in xls.sheet_names:
                    existing_dfs[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
            print(f"[INFO] Mevcut Excel okundu: {len(existing_dfs)} sheet")
        except Exception as e:
            print(f"[WARN] Mevcut Excel okunamadı, yeni dosya oluşturulacak: {e}")
    
    # Birleştir ve temizle
    if "StockDetails" in existing_dfs and not df_details.empty:
        df_details = pd.concat([existing_dfs["StockDetails"], df_details], ignore_index=True)
        df_details = df_details.drop_duplicates(subset=["Tarih", "Ticker"], keep="last")
        df_details = df_details.sort_values(["Tarih", "Ticker"]).reset_index(drop=True)
    
    if "PortfolioSummary" in existing_dfs and not df_summary.empty:
        df_summary = pd.concat([existing_dfs["PortfolioSummary"], df_summary], ignore_index=True)
        df_summary = df_summary.drop_duplicates(subset=["Tarih"], keep="last")
        df_summary = df_summary.sort_values("Tarih").reset_index(drop=True)
    
    if "StockSummary" in existing_dfs and not df_stock_summary.empty:
        df_stock_summary = pd.concat([existing_dfs["StockSummary"], df_stock_summary], ignore_index=True)
        df_stock_summary = df_stock_summary.drop_duplicates(subset=["Ticker"], keep="last")
        df_stock_summary = df_stock_summary.sort_values("Ticker").reset_index(drop=True)
    
    # Excel'e yaz - ÖNEMLİ: StockDetails ilk sırada (ana sheet)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # SIRA ÖNEMLİ: En önemli sheet ilk
        if not df_details.empty:
            df_details.to_excel(writer, sheet_name="StockDetails", index=False)
        if not df_summary.empty:
            df_summary.to_excel(writer, sheet_name="PortfolioSummary", index=False)
        if not df_stock_summary.empty:
            df_stock_summary.to_excel(writer, sheet_name="StockSummary", index=False)
    
    print(f"\n{'='*70}")
    print(f"✅ EXCEL BAŞARIYLA GÜNCELLENDİ")
    print(f"{'='*70}")
    print(f"📁 Dosya: {path}")
    print(f"\n📊 SHEET YAPISI:")
    print(f"  1️⃣  StockDetails (ANA): {len(df_details)} satır")
    print(f"      └─ Her satır = 1 hisse x 1 gün")
    if not df_details.empty:
        tarih_sayisi = df_details['Tarih'].nunique()
        hisse_sayisi = df_details['Ticker'].nunique()
        print(f"      └─ {tarih_sayisi} farklı tarih x {hisse_sayisi} farklı hisse")
    print(f"  2️⃣  PortfolioSummary: {len(df_summary)} satır")
    print(f"      └─ Her satır = 1 günün toplam portföy değeri")
    print(f"  3️⃣  StockSummary: {len(df_stock_summary)} satır")
    print(f"      └─ Her satır = 1 hissenin son durumu")
    print()


# ------------------ MAIN ------------------ #

def main():
    print("\n" + "="*70)
    print("🚀 HİSSE BAZLI GÜN SONU DEĞERLENDİRME")
    print("="*70)
    
    # Verileri çek
    trades = fetch_all_trades()
    if not trades:
        print("[ERROR] Veritabanında hiç işlem bulunamadı.")
        return
    
    ticker_map = fetch_all_stocks()
    print(f"\n📦 Veri Yüklendi:")
    print(f"  - {len(trades)} işlem")
    print(f"  - {len(ticker_map)} hisse")
    
    # Tarih aralığını otomatik tespit et veya manuel kullan
    global TARGET_DATES
    if TARGET_DATES is None:
        # trade_date'leri normalize et
        for t in trades:
            if isinstance(t["trade_date"], datetime):
                t["trade_date"] = t["trade_date"].date()
        
        unique_dates = sorted(set(t["trade_date"] for t in trades))
        
        if not unique_dates:
            print("[ERROR] Hiç işlem tarihi bulunamadı.")
            return
        
        print(f"\n📅 Veritabanındaki İşlem Tarihleri:")
        print(f"  - İlk işlem: {unique_dates[0]}")
        print(f"  - Son işlem: {unique_dates[-1]}")
        print(f"  - Toplam {len(unique_dates)} farklı gün")
        
        # Kullanıcıya seçenek sun
        print(f"\n⚙️  Analiz Modu:")
        print(f"  1) Son 2 günü analiz et: {unique_dates[-2:] if len(unique_dates) >= 2 else unique_dates}")
        print(f"  2) Tüm günleri analiz et: {unique_dates[0]} ~ {unique_dates[-1]} ({len(unique_dates)} gün)")
        print(f"  3) Belirli tarihleri manuel gir")
        
        choice = input("\nSeçiminiz (1/2/3) [varsayılan: 1]: ").strip() or "1"
        
        if choice == "1":
            TARGET_DATES = unique_dates[-2:] if len(unique_dates) >= 2 else unique_dates
        elif choice == "2":
            TARGET_DATES = unique_dates
        elif choice == "3":
            print("\nTarih formatı: YYYY-MM-DD (örnek: 2025-12-08)")
            date_input = input("Analiz edilecek tarihleri virgülle ayırarak girin: ").strip()
            try:
                TARGET_DATES = [datetime.strptime(d.strip(), "%Y-%m-%d").date() 
                               for d in date_input.split(",")]
                TARGET_DATES = sorted(TARGET_DATES)
            except ValueError:
                print("[ERROR] Geçersiz tarih formatı. Son 2 gün kullanılacak.")
                TARGET_DATES = unique_dates[-2:] if len(unique_dates) >= 2 else unique_dates
        else:
            print("[WARN] Geçersiz seçim. Son 2 gün kullanılacak.")
            TARGET_DATES = unique_dates[-2:] if len(unique_dates) >= 2 else unique_dates
        
        print(f"\n✓ Analiz edilecek tarihler: {', '.join(str(d) for d in TARGET_DATES)}")
    else:
        print(f"\n📅 Manuel olarak belirtilen tarih aralığı: {TARGET_DATES[0]} - {TARGET_DATES[-1]}")
    
    print("="*70)
    
    # Analiz yap
    summary_rows, detail_rows, stock_summary_rows = build_stock_level_history(
        trades=trades,
        ticker_map=ticker_map,
        dates=TARGET_DATES,
    )
    
    # Excel'e yaz
    if summary_rows or detail_rows or stock_summary_rows:
        update_excel_improved(summary_rows, detail_rows, stock_summary_rows, EXCEL_PATH)
        print("✨ İşlem tamamlandı!")
    else:
        print("\n[WARN] Hiçbir satır üretilemedi - Excel güncellenemedi")


if __name__ == "__main__":
    main()