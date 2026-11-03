"""Sınıfa duyarlı sembol çözümleme ve ortak ölçü birimi sabitleri."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.asset_symbols import resolve_yf_symbol
from src.domain.models.asset import AssetClass
from src.domain.units import TROY_OUNCE_GRAMS, ounce_price_to_gram_price


@pytest.mark.parametrize(
    "asset_class,symbol,expected",
    [
        (AssetClass.US_STOCK, "aapl", "AAPL"),
        (AssetClass.US_STOCK, " nvda ", "NVDA"),
        (AssetClass.US_STOCK, "BRK.B", "BRK-B"),   # tek harfli hisse sınıfı: Yahoo yazımı
        (AssetClass.US_STOCK, "asml.as", "ASML.AS"),   # borsa eki olduğu gibi kalır
        (AssetClass.CRYPTO, "btc", "BTC-USD"),
        (AssetClass.CRYPTO, "eth-eur", "ETH-EUR"),
        (AssetClass.PRECIOUS_METAL, "gc=f", "GC=F"),
    ],
)
def test_resolves_symbol_without_bist_suffix(asset_class, symbol, expected):
    resolved = resolve_yf_symbol(asset_class, symbol)

    assert resolved == expected
    assert not resolved.endswith(".IS")


def test_index_and_multi_symbol_text_are_rejected():
    with pytest.raises(ValueError, match="ETF"):
        resolve_yf_symbol(AssetClass.US_STOCK, "^ixic")
    with pytest.raises(ValueError, match="tek sembol"):
        resolve_yf_symbol(AssetClass.US_STOCK, "AAPL MSFT")


def test_empty_symbol_is_rejected():
    with pytest.raises(ValueError):
        resolve_yf_symbol(AssetClass.CRYPTO, "  ")


def test_ounce_constant_is_shared_with_existing_services():
    from src.application.services.analysis.benchmark_service import AnalysisBenchmarkService
    from src.application.services.market import market_indicators_service

    assert TROY_OUNCE_GRAMS == Decimal("31.1034768")
    assert AnalysisBenchmarkService.TROY_OUNCE_GRAMS is TROY_OUNCE_GRAMS
    assert market_indicators_service.TROY_OZ_TO_GRAM == float(TROY_OUNCE_GRAMS)


def test_ounce_price_to_gram_price():
    assert ounce_price_to_gram_price(TROY_OUNCE_GRAMS * 100) == Decimal("100")
