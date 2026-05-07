"""
MERKO.IS — Bedelsiz Sermaye Artırımı Uygulama Scripti
=======================================================
Ex-date  : 05-05-2026
Oran     : %638.34  (her 100 hisseye 638.34 bedelsiz hisse)
Referans : 04-05-2026 kapanış fiyatı (bölünme öncesi son fiyat)

Yapılanlar:
  1. MERKO.IS stock_id bulunur
  2. 04-05-2026 fiyatı DB'den okunur (teorik baz fiyat gösterimi için)
  3. Bedelsiz aksiyon DB'ye kaydedilir (corporate_actions tablosu)
  4. Portföye uygulanır (sentetik BUY trade eklenir, lot sayısı artar)
  5. YFinance'den MERKO.IS geçmiş fiyatları retroaktif olarak güncellenir
"""

import sys
import os
from datetime import date, timedelta
from decimal import Decimal

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.application.container import AppContainer

# ──────────────── Parametreler ────────────────
TICKER      = "MERKO.IS"
EX_DATE     = date(2026, 5, 5)
REF_DATE    = date(2026, 5, 4)   # Bölünme öncesi son işlem günü
RATIO_PCT   = Decimal("638.34")  # % olarak
RATIO       = RATIO_PCT / Decimal("100")   # 6.3834
NOTES       = "KAP duyurusu: %638.34 bedelsiz sermaye artırımı, ex-date 05.05.2026"
# ───────────────────────────────────────────────


def main():
    print("=" * 60)
    print(f"  MERKO.IS Bedelsiz Sermaye Artırımı — %{RATIO_PCT}")
    print("=" * 60)

    # 1) Container başlat
    print("\n[1/5] Veritabanı bağlantısı kuruluyor...")
    try:
        container = AppContainer()
    except Exception as e:
        print(f"  HATA: {e}")
        sys.exit(1)
    print("  OK")

    # 2) MERKO.IS stock_id bul
    print(f"\n[2/5] {TICKER} hissesi aranıyor...")
    stock = container.stock_repo.get_stock_by_ticker(TICKER)
    if stock is None:
        print(f"  HATA: {TICKER} portföyde bulunamadı. Ticker adını kontrol edin.")
        sys.exit(1)
    print(f"  Bulundu -> stock_id={stock.id}, isim='{stock.name}'")

    # 3) 04-05-2026 referans fiyatını oku
    print(f"\n[3/5] {REF_DATE} referans fiyatı okunuyor...")
    try:
        daily = container.price_repo.get_price_for_date(stock.id, REF_DATE)
        if daily:
            ref_price = Decimal(str(daily.close_price))
            print(f"  Referans fiyat ({REF_DATE}): {ref_price:.4f} TL")
            theoretical = ref_price / (Decimal("1") + RATIO)
            print(f"  Teorik baz fiyat (ex-date sonrası): {theoretical:.4f} TL")
        else:
            ref_price = None
            print(f"  Uyarı: {REF_DATE} için DB'de fiyat yok. Teorik hesap atlanacak.")
    except Exception as e:
        ref_price = None
        print(f"  Uyarı: Fiyat okunamadı ({e}). Devam ediliyor...")

    # 4) Mevcut MERKO pozisyonunu göster
    print(f"\n[4/5] Mevcut MERKO pozisyonu:")
    trades = container.portfolio_repo.get_trades_by_stock(stock.id)
    from src.domain.models.position import Position
    position = Position.from_trades(stock.id, trades)

    if position.total_quantity == 0:
        print("  HATA: Portföyde MERKO.IS pozisyonu yok!")
        sys.exit(1)

    new_shares = int(Decimal(str(position.total_quantity)) * RATIO)
    print(f"  Mevcut Lot    : {position.total_quantity:,}")
    print(f"  Ort. Maliyet  : {position.average_cost:.4f} TL")
    print(f"  Toplam Maliyet: {position.total_cost:.2f} TL")
    print(f"  Yeni Lot (+)  : {new_shares:,}")
    print(f"  Toplam Lot    : {position.total_quantity + new_shares:,}")
    new_avg = position.total_cost / Decimal(str(position.total_quantity + new_shares))
    print(f"  Yeni Ort. Mal.: {new_avg:.4f} TL")

    # 5) Aksiyonu kaydet ve uygula
    print(f"\n[5/5] Bedelsiz sermaye artırımı uygulanıyor...")

    try:
        action = container.corporate_action_service.register_bedelsiz(
            stock_id=stock.id,
            ex_date=EX_DATE,
            ratio=RATIO,
            notes=NOTES,
        )
        print(f"  Aksiyon kaydedildi -> action_id={action.id}")
    except Exception as e:
        print(f"  HATA: Aksiyon kaydedilemedi: {e}")
        sys.exit(1)

    try:
        result = container.corporate_action_service.apply_action(
            action_id=action.id,
            current_price=Decimal(str(ref_price)) if ref_price else None,
        )
        print(f"  Uygulandı!")
        print(f"  {result.shares_before:,} lot + {result.new_shares:,} yeni lot = {result.shares_after:,} lot")
        print(f"  Ort. Maliyet: {result.avg_cost_before:.4f} -> {result.avg_cost_after:.4f} TL")
        if result.theoretical_ex_price:
            print(f"  Teorik Baz Fiyat: {result.theoretical_ex_price:.4f} TL")
    except Exception as e:
        print(f"  HATA: Aksiyon uygulanamadı: {e}")
        sys.exit(1)

    # 6) YFinance'den retroaktif fiyat güncellemesi
    print(f"\n[+] {TICKER} geçmiş fiyatları YFinance'den güncelleniyor...")
    try:
        first_date = container.portfolio_service.get_first_trade_date()
        if first_date is None:
            first_date = EX_DATE - timedelta(days=365 * 3)

        updated = container.backfill_service.backfill_for_single_stock(
            stock_id=stock.id,
            ticker=TICKER,
            start_date=first_date,
            end_date=date.today(),
        )
        print(f"  {updated} fiyat kaydı güncellendi ({first_date} — {date.today()})")
    except Exception as e:
        print(f"  Uyarı: Fiyat güncellemesi başarısız: {e}")
        print("  Fiyatlar 'Fiyatları Güncelle' butonuyla manuel güncellenebilir.")

    print()
    print("=" * 60)
    print("  TAMAMLANDI")
    print(f"  MERKO.IS: {result.shares_before:,} lot -> {result.shares_after:,} lot")
    print(f"  Yeni ortalama maliyet: {result.avg_cost_after:.4f} TL")
    print("=" * 60)


if __name__ == "__main__":
    main()
