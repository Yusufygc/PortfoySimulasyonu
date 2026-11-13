"""Yolculuk 3: Kullanıcı BIST dışı varlık ekler (çevrimdışı hata + doğrulanmış ekleme), USD alır, NASDAQ hissesi alır,
sınıf sekmelerini ve TRY/USD anahtarını dener.

Plan kimlikleri: PF-001, PF-002, PF-003, PF-004, PF-010, PF-012 (docs/wiki/product_test_plan.md).
"""
from decimal import Decimal

import pytest

from tests.e2e.seed import FakeSymbolVerifier, seed_asset_prices, seed_fx
from tests.e2e.test_02_cash_and_trades import fmt_date, last_weekday


def usd_balance(human) -> Decimal:
    return human.container.cash_pool_service.usd_balance()


def tl_balance(human) -> Decimal:
    return human.container.portfolio_service.get_cash_balance()


def asset_symbols(human):
    return [a.symbol for a in human.container.asset_ledger_service.list_assets()]


@pytest.fixture(scope="module", autouse=True)
def fx_history(human):
    seed_fx(human.container)


def test_adding_asset_offline_fails_with_clear_message_and_adds_nothing(human):
    """[PF-003][NEG] İnternet yokken katalogdan NASDAQ hissesi eklenmeye çalışılır: açık hata, varlık eklenmez, arayüz donmaz."""
    human.open_page("Portföyüm")
    human.click("Varlık Ekle", exact=True)
    assert human.wait_sees("Hazır Varlıklar")
    human.click("AAPL · Apple")
    assert human.wait_sees("doğrulanamadı", timeout=8), f"Hata mesajı yok: {human.visible_texts()[-15:]}"
    human.settle(10)
    assert "AAPL" not in asset_symbols(human)
    human.screenshot("varlik_ekle_cevrimdisi")
    human.cancel()


def test_add_nasdaq_stock_from_catalog_when_source_confirms(human):
    """[PF-003] Kaynak sembolü ve USD para birimini doğrulayınca NVDA katalogdan eklenir; kutu kapanır, sınıf sekmesi sayar."""
    human.container.asset_ledger_service._symbol_verifier = FakeSymbolVerifier({"NVDA": "USD", "AAPL": "USD"})
    human.open_page("Portföyüm")
    human.click("Varlık Ekle", exact=True)
    assert human.wait_sees("Hazır Varlıklar")
    human.click("NVDA · NVIDIA")
    assert human.wait_until(lambda: "NVDA" in asset_symbols(human), 10), "NVDA eklenmedi"
    human.settle(10)
    human.cancel()
    asset = next(a for a in human.container.asset_ledger_service.list_assets() if a.symbol == "NVDA")
    assert asset.quote_currency == "USD" and asset.asset_class.value == "US_STOCK"
    seed_asset_prices(human.container, asset, 410, seed=5)


def test_buy_usd_from_tl_cash_pool(human):
    """[PF-010] Döviz Al: 1000 USD @ 50 TL. USD nakit 1000, TL nakit 50.000 TL azalır."""
    tl_before = tl_balance(human)
    human.open_page("Portföyüm")
    human.click("Döviz Al/Sat", exact=True)
    assert human.wait_sees("USD Miktarı")
    human.fill("USD Miktarı", "1000")
    human.fill("Kur (1 USD = ? TL)", "50")
    human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday(2)))
    human.fill("İşlem Saati (SS:DD)", "12:00")
    human.click("USD AL", nth=1, exact=True)                # 0: sekme, 1: onay düğmesi
    assert human.wait_until(lambda: usd_balance(human) == Decimal("1000"), 8), \
        f"USD alınmadı. Ekran: {human.visible_texts()[-25:]}"
    assert tl_balance(human) == tl_before - Decimal("50000")
    human.cancel()
    human.screenshot("usd_alindi")


def test_buy_usd_with_more_than_tl_cash_is_rejected(human):
    """[PF-010][GLB-004] TL nakitten fazla USD alımı reddedilir, bakiyeler değişmez."""
    usd_before, tl_before = usd_balance(human), tl_balance(human)
    human.open_page("Portföyüm")
    human.click("Döviz Al/Sat", exact=True)
    human.fill("USD Miktarı", "100000000")
    human.fill("Kur (1 USD = ? TL)", "50")
    human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday(2)))
    human.fill("İşlem Saati (SS:DD)", "12:30")
    human.click("USD AL", nth=1, exact=True)
    human.pump(30, 0.01)
    assert usd_balance(human) == usd_before and tl_balance(human) == tl_before


def test_buy_nasdaq_stock_with_usd_and_see_it_in_us_tab(human):
    """[PF-004] Varlık İşlemi: NVDA 2 adet @ 400 USD (kur 50). USD nakit 200'e düşer; ABD Hisseleri sekmesinde görünür."""
    human.open_page("Portföyüm")
    human.click("Varlık İşlemi", exact=True)
    assert human.wait_sees("Tahmini Tutar")
    human.fill("Miktar", "2")
    human.fill("Birim Fiyat", "400")
    human.fill("Kur (1 birim kaç TRY)", "50")
    human.fill("İşlem Tarihi (GG.AA.YYYY)", fmt_date(last_weekday(1)))
    human.fill("İşlem Saati (SS:DD)", "15:00")
    human.click("ALIM", nth=1, exact=True)
    assert human.wait_until(lambda: usd_balance(human) == Decimal("200"), 8), \
        f"Alım olmadı. USD={usd_balance(human)} Ekran: {human.visible_texts()[-25:]}"
    human.settle()
    human.cancel()
    human.click("ABD Hisseleri (1)")
    assert human.wait_sees("NVDA")
    human.screenshot("abd_sekmesi")


def test_class_tabs_filter_rows_and_empty_class_says_so(human):
    """[PF-001] Kripto sekmesi boştur ve bunu söyler; Tümü sekmesi BIST ve ABD pozisyonunu birlikte gösterir."""
    human.open_page("Portföyüm")
    human.click("Kripto (0)")
    assert human.wait_sees("Bu sınıfta pozisyon yok")
    human.click("Tümü (2)")
    assert human.wait_sees("NVDA") and human.wait_sees("THYAO")


def test_currency_switch_shows_usd_totals_and_returns_to_try(human):
    """[PF-002] USD anahtarı toplamları $ ile gösterir; TRY'ye dönünce ₺ döner."""
    human.open_page("Portföyüm")
    human.click("USD", exact=True)
    assert human.wait_until(lambda: any(t.startswith("$") for t in human.visible_texts()), 6), human.visible_texts()[:60]
    human.click("TRY", exact=True)
    assert human.wait_until(lambda: any(t.startswith("₺") for t in human.visible_texts()), 6)


def test_asset_with_open_position_cannot_be_removed(human):
    """[PF-012] Açık pozisyonlu varlığın Kaldır düğmesi gerekçeli uyarı verir; varlık takipte kalır."""
    human.open_page("Portföyüm")
    human.click("ABD Hisseleri (1)")
    reason = human.c["assetsController"].removeBlockReason(
        next(a.id for a in human.container.asset_ledger_service.list_assets() if a.symbol == "NVDA"))
    assert "açık pozisyon" in reason
    assert "NVDA" in asset_symbols(human)
