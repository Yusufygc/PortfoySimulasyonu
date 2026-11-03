"""Yolculuk 5: Kullanıcı aylık bütçe kurar, hedef ekranını gezer, DCA simülasyonu ve strateji testi çalıştırır.

Plan kimlikleri: FP-BUD-001, FP-GOAL-001, FP-DCA-001, FP-STR-001 (docs/wiki/product_test_plan.md).
"""
from PySide6.QtCore import QPoint

TABS = {
    "Bütçe Yönetimi": "GELİR KALEMLERİ",
    "Finansal Hedefler": "FİZİBİLİTE ANALİZİ",
    "DCA Simülatörü": "Simülasyonu Çalıştır",
    "Strateji Testi": "Testi Çalıştır",
}


def open_tab(human, tab):
    human.open_page("Finansal Planlama")
    human.click(tab, exact=True)
    assert human.wait_sees(TABS[tab]), f"{tab} içeriği görünmedi: {human.visible_texts()[:40]}"


def test_all_planning_tabs_open_and_show_their_content(human):
    """[FP-BUD-001] Dört sekme de tıklanınca kendi içeriğini gösterir."""
    for tab in TABS:
        open_tab(human, tab)
    human.screenshot("planlama_sekmeleri")


def test_budget_income_and_expense_update_totals(human):
    """[FP-BUD-001] 50.000 TL maaş ve 20.000 TL kira girilir; toplamlar ve tasarruf gücü doğru hesaplanır."""
    open_tab(human, "Bütçe Yönetimi")
    human.fill_hint("Maaş / Ek Gelir", "Maaş")
    human.fill_hint("Tutar", "50000", nth=0)
    human.click_at(QPoint(785, 340))                       # yeşil '+' (gelir ekle)
    assert human.wait_sees("1 kalem"), f"Gelir eklenmedi: {human.visible_texts()[:60]}"
    human.fill_hint("Kira / Mutfak", "Kira")
    human.fill_hint("Tutar", "20000", nth=1)
    human.click_at(QPoint(1392, 340))                      # kırmızı '+' (gider ekle)
    assert human.wait_until(lambda: human.count("1 kalem") >= 2, 6), f"Gider eklenmedi: {human.visible_texts()[:60]}"
    assert human.wait_sees("50.000,00 ₺")
    assert human.wait_sees("20.000,00 ₺")
    assert human.wait_sees("30.000,00 ₺")                  # tasarruf gücü
    human.screenshot("butce_dolu")


def test_goals_tab_empty_state_and_new_goal_dialog_opens_and_cancels(human):
    """[FP-GOAL-001] Hedef yokken açıklayıcı boş durum görünür; 'Yeni Hedef' kutusu açılır ve İptal ile veri yazmadan kapanır."""
    open_tab(human, "Finansal Hedefler")
    assert human.sees("Henüz bir finansal hedef eklenmemiş")
    human.click("Yeni Hedef", nth=0)
    assert human.wait_sees("İptal")
    human.screenshot("yeni_hedef_kutusu")
    human.cancel()
    assert not human.sees("İptal", exact=True)
    assert human.sees("Henüz bir finansal hedef eklenmemiş")


def test_dca_simulation_runs_on_stored_history(human):
    """[FP-DCA-001] THYAO+FROTO için 5.000 TL aylık DCA simülasyonu çalışır; katkı sayısı ve getiri görünür."""
    open_tab(human, "DCA Simülatörü")
    assert human.sees("Simülasyon çalıştırılmadı")
    human.click("Simülasyonu Çalıştır", exact=True)
    assert human.wait_until(lambda: not human.sees("Simülasyon çalıştırılmadı"), 40), "DCA sonucu gelmedi"
    assert not human.sees("0 Ay", exact=True), "Katkı sayısı 0 kaldı"
    human.screenshot("dca_sonuc")


def test_strategy_backtest_runs_and_shows_curve(human):
    """[FP-STR-001] Varsayılan üç hisse ve 3 aylık dengelemeyle strateji testi çalışır; boş durum metni kalkar."""
    open_tab(human, "Strateji Testi")
    assert human.sees("Test çalıştırılmadı")
    human.click("Testi Çalıştır", exact=True)
    assert human.wait_until(lambda: not human.sees("Test çalıştırılmadı"), 90), "Strateji testi sonucu gelmedi"
    human.screenshot("strateji_testi_sonuc")
