"""Yolculuk 8: Kullanıcı uygulamayı kapatıp yeniden açar (veriler kalır), sonra sistemi sıfırlar (her şey temizlenir).

Plan kimlikleri: GLB-003, SET-007, BG-002 (docs/wiki/product_test_plan.md).
Not: Bu dosya adı gereği en sonda çalışır; sıfırlama diğer yolculukların verisini siler.
"""
from decimal import Decimal


def test_data_survives_app_restart(human):
    """[GLB-003] Yeni bir AppContainer aynı veritabanını açınca nakit, pozisyon, varlık, izleme listesi, model portföy kalır."""
    from src.application.container import AppContainer

    reopened = AppContainer()
    assert reopened.portfolio_service.get_cash_balance() == human.container.portfolio_service.get_cash_balance()
    assert reopened.portfolio_service.get_cash_balance() > Decimal("0")
    positions = reopened.portfolio_service.get_current_portfolio().positions
    assert any(p.total_quantity == 60 for p in positions.values()), "THYAO 60 lot yeniden açılışta yok"
    assert [a.symbol for a in reopened.asset_ledger_service.list_assets()] == ["NVDA"]
    assert [w.name for w in reopened.watchlist_service.get_all_watchlists()] == ["Teknoloji"]
    assert reopened.cash_pool_service.usd_balance() == Decimal("200")
    assert reopened.fee_settings_service.bist_fee(Decimal("10000")) == Decimal("20")


def open_reset_dialog(human):
    human.open_page("Ayarlar")
    human.click("Sistem", exact=True)
    assert human.wait_sees("Sistemi Sıfırla")
    human.click("Sistemi Sıfırla", exact=True)
    assert human.wait_sees("Portföyü Sıfırla"), f"Onay kutusu açılmadı: {human.visible_texts()[-15:]}"


def test_system_reset_asks_for_confirmation_and_cancel_keeps_data(human):
    """[SET-007] 'Sistemi Sıfırla' onay ister; Vazgeç veriyi korur."""
    before = human.container.portfolio_service.get_cash_balance()
    open_reset_dialog(human)
    human.screenshot("sifirlama_onayi")
    human.click("Vazgeç", exact=True)
    human.pump(30, 0.02)
    assert not human.sees("Portföyü Sıfırla")
    assert human.container.portfolio_service.get_cash_balance() == before


def test_system_reset_confirmed_clears_everything_and_pages_show_empty_states(human):
    """[SET-007] Onaylanan sıfırlama nakit, işlem, varlık ve listeleri siler; sayfalar boş durumla açılır."""
    open_reset_dialog(human)
    human.click_beside("Vazgeç", "Sistemi Sıfırla")
    assert human.wait_until(lambda: human.container.portfolio_service.get_cash_balance() == Decimal("0"), 15),         "Sıfırlama nakdi temizlemedi"
    assert human.container.portfolio_service.get_current_portfolio().positions == {}
    assert human.container.asset_ledger_service.list_assets() == []
    assert human.container.watchlist_service.get_all_watchlists() == []
    human.open_page("Portföyüm")
    assert human.wait_sees("Bu sınıfta pozisyon yok")
    human.screenshot("sifirlama_sonrasi")
