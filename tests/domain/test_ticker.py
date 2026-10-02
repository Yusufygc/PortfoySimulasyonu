import pytest

from src.domain.ticker import clean_ticker, to_yf_symbol


@pytest.mark.parametrize("raw,expected", [
    ("THYAO", "THYAO"), ("thyao.is", "THYAO"), (" ASELS.IS ", "ASELS"), ("", ""), (None, ""), ("XU100.IS", "XU100"),
])
def test_clean_ticker(raw, expected):
    assert clean_ticker(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("THYAO", "THYAO.IS"), ("thyao.is", "THYAO.IS"), ("^XU100", "^XU100"), ("USDTRY=X", "USDTRY=X"),
    ("SAP.DE", "SAP.DE"), ("", ""), (None, ""),
])
def test_to_yf_symbol(raw, expected):
    assert to_yf_symbol(raw) == expected
