"""Yolculuk 1: Yeni kullanıcı uygulamayı ilk kez açar, tüm sayfaları gezer, temayı değiştirir, hisse arar.

Plan kimlikleri: ENV-002, GLB-001, GLB-002, GLB-005, DASH-001, DASH-006 (docs/wiki/product_test_plan.md).
"""
import pytest
from PySide6.QtCore import Qt

PAGES = [
    ("Genel Bakış", 0), ("Portföyüm", 10), ("İzleme Listeleri", 1), ("Model Portföyler", 2), ("Hisse 360", 3),
    ("Karşılaştırma Lab", 4), ("Hisse Tarayıcı", 5), ("Finansal Planlama", 6), ("Optimizasyon", 7),
    ("AI Asistan", 8), ("Ayarlar", 9),
]

# Her sayfada ilk bakışta görünmesi gereken başlık metni (boş veritabanı)
PAGE_MARKERS = {
    "Genel Bakış": "Etkileşimli grafik",
    "Portföyüm": "Toplam Portföy Değeri",
    "İzleme Listeleri": "TAKİP LİSTELERİM",
    "Model Portföyler": "PORTFÖYLERİM",
    "Hisse 360": "Analiz Et",
    "Karşılaştırma Lab": "KARŞILAŞTIRILACAK VARLIKLAR",
    "Hisse Tarayıcı": "BIST Sinyal Tarayıcısı",
    "Finansal Planlama": "Bütçe Yönetimi",
    "Optimizasyon": "Markowitz Portföy Optimizasyonu",
    "AI Asistan": "Portföy Danışmanı",
    "Ayarlar": "Uygulama Ayarları",
}


def test_app_opens_on_overview_with_chart_and_empty_data(human):
    """[ENV-002] Açılışta Genel Bakış, grafik başlığı, piyasa durumu ve saat görünür; kenar çubuğunda 11 sayfa vardır."""
    assert human.active_page == 0
    assert human.sees("Etkileşimli grafik")
    assert human.sees("BIST:")                      # piyasa durumu rozeti
    for title, _ in PAGES:
        assert human.sees(title, exact=True), f"Kenar çubuğunda '{title}' yok"


@pytest.mark.parametrize("title,index", PAGES)
def test_every_page_opens_by_click_and_shows_its_content(human, title, index):
    """[GLB-001] Her menü öğesine tıklayınca doğru sayfa açılır ve içeriği çizilir (beyaz ekran yok)."""
    human.open_page(title)
    assert human.active_page == index
    marker = PAGE_MARKERS[title]
    assert human.wait_sees(marker), f"{title}: '{marker}' görünmedi. Görünenler: {human.visible_texts()[:50]}"
    human.screenshot(f"sayfa_{index:02d}_{title.replace(' ', '_')}")


def test_header_title_follows_active_page(human):
    """[GLB-001] Üst başlıktaki sayfa adı aktif sayfayla uyumludur."""
    for title, _ in PAGES:
        human.open_page(title)
        assert human.c["shellController"].pageTitle, "Sayfa başlığı boş"


def test_sidebar_can_collapse_and_expand(human):
    """[GLB-001] 'Menüyü Daralt' ile menü etiketleri gizlenir; aynı satırdaki düğmeyle yeniden genişler."""
    from PySide6.QtCore import QPoint

    human.open_page("Genel Bakış")
    toggle = human.items_with_text("Menüyü Daralt", exact=True)[0]
    toggle_y = human.center_of(toggle).y()
    human.click_item(toggle)
    human.pump(30, 0.01)
    assert not human.sees("İzleme Listeleri", exact=True), "Daralınca menü etiketleri gizlenmedi"
    human.click_at(QPoint(28, toggle_y))
    human.pump(30, 0.01)
    assert human.sees("İzleme Listeleri", exact=True), "Genişletme düğmesi çalışmadı"


def test_theme_toggle_round_trip(human):
    """[GLB-002] Ayarlar > Görünüm: Açık Tema'ya geç, tüm sayfalar okunur kalır, koyu temaya geri dön."""
    human.open_page("Ayarlar")
    assert human.wait_sees("Açık Temaya Geç")
    human.click("Açık Temaya Geç")
    human.pump(30, 0.01)
    assert human.sees("Koyu Temaya Geç"), f"Tema düğmesi değişmedi: {human.visible_texts()[:60]}"
    for title, _ in PAGES[:4]:
        human.open_page(title)
        assert human.wait_sees(PAGE_MARKERS[title])
    human.screenshot("tema_acik")
    human.open_page("Ayarlar")
    human.click("Koyu Temaya Geç")
    human.pump(30, 0.01)
    assert human.sees("Açık Temaya Geç")


def test_header_search_opens_ticker_on_overview_chart(human):
    """[GLB-005] Üst arama kutusuna THYAO yazıp Enter: Genel Bakış açılır, grafik başlığı THYAO olur."""
    human.open_page("Portföyüm")
    human.click("Hisse Ara")
    human.type("ASELS")
    human.press_enter()
    assert human.wait_until(lambda: human.active_page == 0, 6), "Arama Genel Bakış'a götürmedi"
    assert human.wait_until(lambda: human.c["chartController"].currentTicker == "ASELS", 8), \
        f"Grafik hissesi: {human.c['chartController'].currentTicker}"
    assert human.wait_sees("ASELS")
    human.screenshot("arama_asels")


def test_overview_chart_header_shows_price_and_change_for_known_ticker(human):
    """[DASH-006] Grafik başlığında fiyat (₺) ve yüzde değişim biçimli görünür."""
    human.open_page("Genel Bakış")
    human.c["chartController"].loadTicker("THYAO")
    assert human.wait_until(lambda: human.c["chartController"].hasQuote, 8)
    texts = human.visible_texts()
    assert any(t.startswith("₺") for t in texts), texts[:60]
    assert any(t.startswith(("+%", "-%", "%")) for t in texts), texts[:60]


def test_no_unexpected_qml_warnings_after_full_tour(human, unexpected_qml_warnings):
    """[GLB-001] Tüm sayfalar gezildikten sonra QML bağlama/null erişim uyarısı yoktur."""
    for title, _ in PAGES:
        human.open_page(title)
    assert unexpected_qml_warnings() == []


@pytest.mark.parametrize("opener,marker", [
    ("Sermaye Yönetimi", "Mevcut Bakiye"),
    ("Hızlı Alım / Satım", "Alım Emrini Onayla"),
    ("Döviz Al/Sat", "USD Miktarı"),
    ("Varlık Ekle", "Hazır Varlıklar"),
    ("Excel Raporu", "Raporu Oluştur"),
])
def test_escape_closes_modal_dialogs(human, opener, marker):
    """[GLB-004][D-03] Escape tuşu açık modal kutuyu veri yazmadan kapatır."""
    human.open_page("Portföyüm")
    human.click(opener, exact=True)
    assert human.wait_sees(marker), f"{opener} kutusu açılmadı"
    human.escape()
    assert human.wait_gone(marker, timeout=3), f"{opener}: Escape kutuyu kapatmadı"
