"""Yolculuk 4: Kullanıcı izleme listesi kurar, hisse ekler/siler; model (sanal) portföy oluşturur.

Plan kimlikleri: WL-001, WL-002, WL-003, MP-001, MP-002 (docs/wiki/product_test_plan.md).
"""
from PySide6.QtCore import QPoint

from tests.e2e.test_02_cash_and_trades import fmt_date, last_weekday


def plus_button(human) -> QPoint:
    """Sayfa başlığının sağındaki mavi '+' düğmesi (metinsiz, ikonlu)."""
    return QPoint(human.window.width() - 34, 94)


def watchlist_names(human):
    return [w["name"] for w in human.c["watchlistController"].watchlists]


def test_create_watchlist_by_clicking_plus(human):
    """[WL-001] '+' ile 'Teknoloji' listesi oluşturulur; liste panelde görünür ve seçilir."""
    human.open_page("İzleme Listeleri")
    human.click_at(plus_button(human))
    assert human.wait_sees("Yeni Takip Listesi Oluştur")
    human.fill("Liste Adı", "Teknoloji")
    human.fill("Açıklama (Opsiyonel)", "Büyük teknoloji ve savunma")
    human.click("Kaydet", exact=True)
    assert human.wait_until(lambda: "Teknoloji" in watchlist_names(human), 6), human.visible_texts()[-20:]
    assert human.wait_sees("1 Liste")
    assert human.container.watchlist_service.get_all_watchlists()[0].description == "Büyük teknoloji ve savunma"
    human.screenshot("izleme_listesi_olustu")


def test_empty_name_is_rejected(human):
    """[WL-001][GLB-004] Boş adla liste oluşturulamaz; liste sayısı değişmez."""
    human.open_page("İzleme Listeleri")
    count = len(watchlist_names(human))
    human.click_at(plus_button(human))
    assert human.wait_sees("Yeni Takip Listesi Oluştur")
    human.click("Kaydet", exact=True)
    human.pump(25, 0.01)
    assert len(watchlist_names(human)) == count


def open_add_stock(human):
    human.open_page("İzleme Listeleri")
    if human.sees("Hisse Ekle", exact=True):                # boş liste: ortadaki düğme
        human.click("Hisse Ekle", exact=True)
    else:                                                   # dolu liste: tablo başlığındaki mavi '+'
        human.click_at(QPoint(human.window.width() - 50, 311))
    assert human.wait_sees("Listeye Hisse Ekle"), f"Hisse ekleme kutusu açılmadı: {human.visible_texts()[-20:]}"


def test_unknown_ticker_is_rejected_and_known_ticker_is_added(human):
    """[WL-002] Bilinmeyen kod (ZZZZZ) reddedilir; bilinen hisse (THYAO) eklenir ve tabloda görünür."""
    results = []
    human.c["watchlistController"].actionCompleted.connect(lambda ok, message: results.append((ok, message)))
    open_add_stock(human)
    human.fill("Hisse Sembolü", "ZZZZZ")
    human.click_beside("İptal", "Hisse Ekle")
    human.pump(40, 0.01)
    assert human.wait_until(lambda: results and not results[-1][0], 6), f"Geçersiz kod için hata bildirimi yok: {results}"
    assert human.c["watchlistController"].currentWatchlistCount == 0, "Geçersiz kod listeye eklendi"
    open_add_stock(human)                                   # kutu her denemeden sonra kapanır
    human.fill("Hisse Sembolü", "THYAO")
    human.fill("Hisseye Dair Notunuz (Strateji / Hedef Fiyat)", "Hedef 300")
    human.click_beside("İptal", "Hisse Ekle")
    assert human.wait_until(lambda: human.c["watchlistController"].currentWatchlistCount == 1, 8),         f"THYAO eklenmedi. Sonuçlar: {results}"
    human.cancel()
    assert human.wait_sees("THYAO")
    human.screenshot("izleme_hisse_eklendi")


def test_adding_same_ticker_twice_does_not_duplicate(human):
    """[WL-002] Aynı hisse ikinci kez eklenmeye çalışılınca listede tek kayıt kalır."""
    open_add_stock(human)
    human.fill("Hisse Sembolü", "THYAO")
    human.click_beside("İptal", "Hisse Ekle")
    human.pump(40, 0.01)
    assert human.c["watchlistController"].currentWatchlistCount == 1


def test_create_model_portfolio_with_initial_capital(human):
    """[MP-001] Yeni model portföy: ad + 100.000 TL başlangıç sermayesiyle oluşturulur ve listede görünür."""
    human.open_page("Model Portföyler")
    human.click("Yeni Portföy")
    assert human.wait_sees("Yeni Portföy Oluştur")
    human.fill("Portföy Adı", "Deneme Sepeti")
    human.click("Kaydet", exact=True)
    assert human.wait_sees("Deneme Sepeti", timeout=8), f"Model portföy listede yok: {human.visible_texts()[-25:]}"
    human.screenshot("model_portfoy_olustu")
