from src.ui.formatters import display_ticker


def test_display_ticker_hides_bist_suffix_only_for_ui():
    assert display_ticker("ASELS.IS") == "ASELS"
    assert display_ticker("THYAO.IS") == "THYAO"
    assert display_ticker("USDTRY=X") == "USDTRY=X"
    assert display_ticker("") == ""
    assert display_ticker(None) == ""
