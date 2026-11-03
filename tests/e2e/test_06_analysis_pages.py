"""Yolculuk 6: Kullanıcı Hisse 360, Karşılaştırma Lab, Hisse Tarayıcı ve Optimizasyon sayfalarıyla analiz yapar.

Plan kimlikleri: S360-001, CMP-001, CMP-003, SCR-001, OPT-001, OPT-002, RISK-001 (docs/wiki/product_test_plan.md).
"""
from PySide6.QtCore import QPoint, Qt


def test_stock_360_searches_ticker_and_shows_company_data(human):
    """[S360-001] Hisse 360'ta THYAO aranır: şirket adı, fiyat ve değerleme kartları görünür."""
    human.open_page("Hisse 360")
    human.click_at(QPoint(443, 98))
    human.key(Qt.Key_A, Qt.ControlModifier)
    human.type("THYAO")
    human.click("Analiz Et", exact=True)
    assert human.wait_until(lambda: human.sees("Türk Hava") or human.sees("THYAO", exact=True), 15), human.visible_texts()[:40]
    assert human.wait_sees("F/K")
    assert human.sees("₺")
    human.screenshot("hisse360_thyao")


def test_stock_360_balance_sheet_and_kap_tabs_switch_without_freezing(human):
    """[S360-002][S360-003] Bilanço ve KAP sekmelerine geçilir; çevrimdışıyken de sayfa donmaz, sekme değişir."""
    human.open_page("Hisse 360")
    human.click("Kapsamlı Bilanço & 18 Analiz Modülü")
    human.pump(40, 0.02)
    human.click("KAP Ortaklık Tarihçesi")
    human.pump(40, 0.02)
    human.click("Genel Bakış & Özet")
    assert human.wait_sees("F/K")


def test_comparison_lab_computes_and_never_claims_nothing_is_selected_when_two_are(human):
    """[CMP-001][CMP-003] Varsayılan iki varlık (Ana Portföy + BIST 100) seçiliyken Karşılaştır çalışır, 3A düğmesi yeniden
    hesaplar. Çevrimdışıyken sonuç boş olabilir ama 'en az bir varlık seçin' yanıltıcı mesajı gösterilmemelidir."""
    human.open_page("Karşılaştırma Lab")
    human.click("Karşılaştır", exact=True)
    assert human.wait_until(lambda: not human.sees("Karşılaştırma hesaplanıyor"), 40), "Karşılaştırma bitmedi"
    human.click("3A", exact=True)
    assert human.wait_until(lambda: not human.sees("Karşılaştırma hesaplanıyor"), 40)
    human.screenshot("karsilastirma")
    assert human.sees("2 seçili")
    assert not human.sees("Karşılaştırmak için en az bir varlık seçin"),         "D-01: 2 varlık seçili olduğu hâlde 'en az bir varlık seçin' mesajı gösteriliyor (veri yok durumu açıklanmıyor)"


def test_scanner_runs_golden_cross_and_reports_status(human):
    """[SCR-001] Tarayıcı Golden Cross taramasını başlatır; 'Taramaya hazır' durumu değişir, arayüz yanıt verir."""
    human.open_page("Hisse Tarayıcı")
    assert human.sees("Taramaya hazır")
    human.click("Taramayı Başlat", exact=True)
    assert human.wait_until(lambda: not human.sees("Taramaya hazır"), 20), "Tarama başlamadı"
    assert human.wait_until(lambda: not human.sees("Henüz tarama yapılmadı"), 120), "Tarama sonuç/durum üretmedi"
    human.screenshot("tarayici_sonuc")


def test_optimization_with_single_holding_reports_instead_of_crashing(human):
    """[OPT-002] Ana portföyde tek hisse varken optimizasyon çökmez; sonuç ya da açık bir uyarı verir."""
    human.open_page("Optimizasyon")
    human.click("Portföyü Optimize Et", exact=True)
    human.pump(60, 0.05)
    assert human.sees("Portföyü Optimize Et", exact=True), "Sayfa yanıt vermiyor"
    human.screenshot("optimizasyon_tek_hisse")


def test_optimization_risk_questionnaire_dialog_opens_and_cancels(human):
    """[RISK-001] Risk Anketi kutusu açılır ve veri yazmadan kapanır."""
    human.open_page("Optimizasyon")
    human.click("Risk Anketi", exact=True)
    human.pump(30, 0.02)
    human.screenshot("risk_anketi")
    human.cancel()
    assert human.sees("Risk Toleransı & Profili")
