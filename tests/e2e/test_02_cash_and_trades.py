"""Yolculuk 2: Kullanıcı sermaye yatırır, BIST hissesi alır/satar, hatalı girişleri dener, Excel raporu alır.

Plan kimlikleri: PF-005, PF-006, PF-007, PF-008, PF-012, GLB-004 (docs/wiki/product_test_plan.md).
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest


def last_weekday(days_back: int = 3) -> date:
    day = date.today() - timedelta(days=days_back)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def fmt_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def cash(human) -> Decimal:
    return human.container.portfolio_service.get_cash_balance()


SEED_CAPITAL = Decimal("250000")


@pytest.fixture(scope="module", autouse=True)
def backdated_capital(human):
    """Kullanıcının geçmişte yatırdığı birikim. Arayüzden yatırılan sermaye 'bugün' tarihlidir ve geçmiş tarihli
    işlemlere yetmez (olay tabanlı nakit kuralı); bu yüzden alım senaryoları için başlangıç sermayesi tohumlanır."""
    if cash(human) == 0:
        human.container.cash_movement_service.add_deposit(SEED_CAPITAL, movement_date=last_weekday(10))
    human.c["dashboardController"].reloadPortfolio()
    human.pump(20, 0.01)


def open_capital(human):
    human.open_page("Portföyüm")
    human.click("Sermaye Yönetimi", exact=True)
    assert human.wait_sees("Mevcut Bakiye")                 # kutu son kullanılan sekmede (yatır/çek) açılır


def test_deposit_capital_updates_cash_everywhere(human):
    """[PF-007] Arayüzden 10.000 TL yatır: nakit kartı, denetleyici ve veritabanı aynı tutarı gösterir."""
    before = cash(human)
    open_capital(human)
    human.click("Nakit Yatır", exact=True)
    human.fill("Tutar (₺)", "10000")
    human.fill("Açıklama / Not", "Ek birikim")
    human.click("Sermaye Yatır", exact=True)
    assert human.wait_until(lambda: cash(human) == before + Decimal("10000"), 6)
    human.cancel()
    assert human.wait_sees("₺260.000,00")
    human.screenshot("sermaye_yatirildi")


def test_withdraw_more_than_balance_is_rejected_with_clear_message(human):
    """[PF-007][GLB-004] Bakiyeden fazla çekme reddedilir, bakiye değişmez, açık Türkçe uyarı çıkar."""
    open_capital(human)
    human.click("Nakit Çek", nth=0, exact=True)             # sekme
    human.fill("Tutar (₺)", "9999999")
    before = cash(human)
    human.click("Nakit Çek", nth=1, exact=True)             # onay düğmesi
    assert human.wait_sees("Yetersiz", timeout=5), f"Uyarı yok: {human.visible_texts()[-25:]}"
    assert cash(human) == before


@pytest.mark.parametrize("bad_amount", ["0", "abc"])
def test_invalid_deposit_amounts_do_not_change_cash(human, bad_amount):
    """[GLB-004] Sıfır ve harf içeren tutar nakdi değiştirmez; uygulama çökmez."""
    before = cash(human)
    open_capital(human)
    human.click("Nakit Yatır", exact=True)
    human.fill("Tutar (₺)", bad_amount)
    human.click("Sermaye Yatır", exact=True)
    human.pump(20, 0.01)
    assert cash(human) == before


def test_minus_sign_is_filtered_from_amount_field(human):
    """[GLB-004] Tutar alanı eksi işaretini kabul etmez: '-50' yazınca alanda '50' görünür (negatif tutar girilemez)."""
    open_capital(human)
    human.click("Nakit Yatır", exact=True)
    human.fill("Tutar (₺)", "-50")
    assert human.value_of("Tutar (₺)") == "50"


def test_quick_buy_thyao_creates_position_and_reduces_cash(human):
    """[PF-005] Hızlı Alım: THYAO 100 lot @ ₺260. Pozisyon tabloda görünür, nakit maliyet kadar düşer."""
    human.open_page("Portföyüm")
    human.click("Hızlı Alım / Satım", exact=True)
    assert human.wait_sees("Alım Emrini Onayla", exact=True)
    human.fill("Hisse Kodu (Ticker)", "THYAO")
    human.fill("Lot Adedi", "100")
    human.fill("Birim Fiyat (₺)", "260")
    human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday()))
    human.fill("İşlem Saati (SS:DD)", "10:30")
    human.screenshot("alim_formu")
    before = cash(human)
    human.click("Alım Emrini Onayla", exact=True)
    ok = human.wait_until(lambda: cash(human) < before, 8)
    assert ok, f"Alım gerçekleşmedi. Ekran: {human.visible_texts()[-30:]}"
    assert cash(human) <= before - Decimal("26000")                      # 100 x 260 + komisyon
    human.cancel()
    assert human.wait_sees("THYAO")
    assert human.wait_sees("1 Açık Pozisyon")
    human.screenshot("alim_sonrasi")


def test_buy_more_than_cash_is_rejected(human):
    """[PF-005][GLB-004] Nakitten büyük alım reddedilir; pozisyon ve nakit değişmez."""
    before = cash(human)
    human.open_page("Portföyüm")
    human.click("Hızlı Alım / Satım", exact=True)
    human.fill("Hisse Kodu (Ticker)", "THYAO")
    human.fill("Lot Adedi", "100000")
    human.fill("Birim Fiyat (₺)", "260")
    human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday()))
    human.fill("İşlem Saati (SS:DD)", "11:00")
    human.click("Alım Emrini Onayla", exact=True)
    assert human.wait_sees("yeterli sermayeniz yoktu", timeout=5), f"Uyarı yok: {human.visible_texts()[-20:]}"
    assert cash(human) == before


def test_sell_more_than_held_is_rejected_and_partial_sell_works(human):
    """[PF-006] Eldekinden fazla satış reddedilir; 40 lot kısmi satış nakdi artırır, 60 lot kalır."""
    human.open_page("Portföyüm")
    human.click("Hızlı Alım / Satım", exact=True)
    human.click("HİSSE SAT (SELL)", exact=True)
    human.fill("Hisse Kodu (Ticker)", "THYAO")
    human.fill("Lot Adedi", "500")
    human.fill("Birim Fiyat (₺)", "270")
    human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday(2)))
    human.fill("İşlem Saati (SS:DD)", "14:00")
    before = cash(human)
    human.click("Satış Emrini Onayla", exact=True)
    assert human.wait_sees("yeterli pozisyonunuz yoktu", timeout=5), f"Uyarı yok: {human.visible_texts()[-20:]}"
    assert cash(human) == before, "Eldekinden fazla satış nakdi değiştirdi"
    # Onay düğmesi kutuyu hemen kapatır; kapanış animasyonu bitmeden karar verilirse kutu fill sırasında kaybolur (yarış)
    if human.wait_gone("Satış Emrini Onayla", timeout=3, exact=True):     # hata sonrası kutu kapandıysa yeniden aç
        human.click("Hızlı Alım / Satım", exact=True)
        human.click("HİSSE SAT (SELL)", exact=True)
        human.fill("Hisse Kodu (Ticker)", "THYAO")
        human.fill("Birim Fiyat (₺)", "270")
        human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday(2)))
        human.fill("İşlem Saati (SS:DD)", "14:00")
    human.fill("Lot Adedi", "40")
    human.click("Satış Emrini Onayla", exact=True)
    assert human.wait_until(lambda: cash(human) > before, 8)
    human.cancel()
    held = {p.stock_id: p.total_quantity for p in human.container.portfolio_service.get_current_portfolio().positions.values()}
    assert 60 in held.values(), held


def test_excel_report_is_created_at_chosen_path(human):
    """[PF-008] Excel Raporu: kayıt yolu yazılır, 'Raporu Oluştur' dosyayı üretir."""
    target = human.work / "rapor.xlsx"
    human.open_page("Portföyüm")
    human.click("Excel Raporu", exact=True)
    assert human.wait_sees("Raporu Oluştur", exact=True)
    human.fill("Kayıt Konumu", str(target))
    human.click("Raporu Oluştur", exact=True)
    assert human.wait_until(target.exists, 15), "Excel dosyası oluşmadı"
    assert target.stat().st_size > 1000
