from src.ui.formatters import display_ticker
from src.ui.shared.locale_tr import L10N


def test_display_ticker_hides_bist_suffix_only_for_ui():
    assert display_ticker("ASELS.IS") == "ASELS"
    assert display_ticker("THYAO.IS") == "THYAO"
    assert display_ticker("USDTRY=X") == "USDTRY=X"
    assert display_ticker("") == ""
    assert display_ticker(None) == ""


def test_dashboard_visible_labels_use_home_page_wording():
    assert L10N.DASHBOARD == "Ana Sayfa"
    assert L10N.DASHBOARD_PORTFOYU == "Ana Portföy"
    assert L10N.POZISYON_KAPANDI_DASHBOARDA_DONULUYOR == "Pozisyon kapandı. Ana Sayfa'ya dönülüyor."
