import pandas as pd
from datetime import date
from decimal import Decimal
import pytest
from yfinance.exceptions import YFException

from src.domain.exceptions import MarketDataUnavailableError
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient
from src.infrastructure.market_data.yfinance_optimization_market_data_provider import (
    YFinanceOptimizationMarketDataProvider,
)
from src.infrastructure.market_data.yfinance_price_lookup_provider import YFinancePriceLookupProvider

def test_get_closing_price_success(monkeypatch):
    client = YFinanceMarketDataClient()
    
    # Create dummy dataframe representing a yfinance response
    df = pd.DataFrame({"Close": [10.5]}, index=[pd.Timestamp("2026-01-01")])
    
    download_calls = []
    def mock_download(tickers, start, end):
        download_calls.append((tickers, start, end))
        return df
        
    monkeypatch.setattr(client, "_download_dataframe", mock_download)
    
    price = client.get_closing_price(1, "THYAO", date(2026, 1, 1))
    assert price == Decimal("10.5")
    assert len(download_calls) == 1
    # kanonik ticker uzantısızdır; yfinance sınırında `.IS` eklenir
    assert download_calls[0] == ("THYAO.IS", date(2026, 1, 1), date(2026, 1, 2))

def test_get_closing_price_empty_response(monkeypatch):
    client = YFinanceMarketDataClient()
    df = pd.DataFrame()
    
    monkeypatch.setattr(client, "_download_dataframe", lambda *a: df)
    
    with pytest.raises(ValueError, match="THYAO.IS icin 2026-01-01 gun sonu fiyati bulunamadi"):
        client.get_closing_price(1, "THYAO", date(2026, 1, 1))

def test_get_price_series(monkeypatch):
    client = YFinanceMarketDataClient()
    
    df = pd.DataFrame({"Close": [100.0, 101.5, 102.0]}, 
                      index=pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"]))  # BIST işlem günleri
                      
    download_calls = []
    def mock_download(tickers, start, end):
        download_calls.append((tickers, start, end))
        return df
        
    monkeypatch.setattr(client, "_download_dataframe", mock_download)
    
    series = client.get_price_series("THYAO", date(2026, 1, 5), date(2026, 1, 7))
    assert series == {
        date(2026, 1, 5): Decimal("100.0"),
        date(2026, 1, 6): Decimal("101.5"),
        date(2026, 1, 7): Decimal("102.0"),
    }


def test_download_dataframe_wraps_yfinance_failures(monkeypatch):
    client = YFinanceMarketDataClient()

    def fail_download(**_kwargs):
        raise YFException("rate limited")

    monkeypatch.setattr("src.infrastructure.market_data.yfinance_client.yf.download", fail_download)

    with pytest.raises(MarketDataUnavailableError, match="YFinance indirme hatasi"):
        client._download_dataframe("AAPL", date(2026, 1, 1), date(2026, 1, 2))


def test_price_lookup_returns_none_when_history_fails(monkeypatch):
    class FakeTicker:
        fast_info = {}
        info = {}

        def history(self, **_kwargs):
            raise YFException("history unavailable")

    monkeypatch.setattr(
        "src.infrastructure.market_data.yfinance_price_lookup_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    assert YFinancePriceLookupProvider().lookup("AAPL") is None


def test_optimization_last_price_returns_none_on_yfinance_failure(monkeypatch):
    class FakeTicker:
        @property
        def fast_info(self):
            raise YFException("ticker unavailable")

    monkeypatch.setattr(
        "src.infrastructure.market_data.yfinance_optimization_market_data_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )

    assert YFinanceOptimizationMarketDataProvider().get_last_price("AAPL") is None


def test_get_price_series_keeps_explicit_exchange_suffix_and_index_symbols(monkeypatch):
    client = YFinanceMarketDataClient()
    df = pd.DataFrame({"Close": [1.0, 2.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    seen = []
    monkeypatch.setattr(client, "_download_dataframe", lambda tickers, start, end: seen.append(tickers) or df)

    client.get_price_series("^XU100", date(2026, 1, 1), date(2026, 1, 2))
    client.get_price_series("sap.de", date(2026, 1, 1), date(2026, 1, 2))
    client.get_price_series("asels.is", date(2026, 1, 1), date(2026, 1, 2))

    assert seen == ["^XU100", "SAP.DE", "ASELS.IS"]


def test_download_dataframe_requests_unadjusted_prices(monkeypatch):
    """SQLite fiyat politikası: ham kapanış (bölünme düzeltmeli `Close`), temettü düzeltmesi yok."""
    client = YFinanceMarketDataClient()
    seen = {}

    def fake_download(**kwargs):
        seen.update(kwargs)
        return pd.DataFrame()

    monkeypatch.setattr("src.infrastructure.market_data.yfinance_client.yf.download", fake_download)
    client._download_dataframe("THYAO.IS", date(2026, 1, 1), date(2026, 1, 2))

    assert seen["auto_adjust"] is False


def test_get_price_series_uses_close_not_adj_close(monkeypatch):
    client = YFinanceMarketDataClient()
    index = pd.to_datetime(["2026-01-05", "2026-01-06"])
    df = pd.DataFrame({"Close": [10.26, 9.98], "Adj Close": [9.90, 9.63]}, index=index)
    monkeypatch.setattr(client, "_download_dataframe", lambda tickers, start, end: df)

    series = client.get_price_series("UNLU", date(2026, 1, 5), date(2026, 1, 6))

    assert series == {date(2026, 1, 5): Decimal("10.26"), date(2026, 1, 6): Decimal("9.98")}


def test_price_lookup_history_requests_unadjusted_prices(monkeypatch):
    seen = {}

    class FakeTicker:
        fast_info = {}
        info = {}

        def history(self, **kwargs):
            seen.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        "src.infrastructure.market_data.yfinance_price_lookup_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )
    YFinancePriceLookupProvider().lookup("THYAO.IS")

    assert seen["auto_adjust"] is False


def test_price_lookup_history_timestamp_is_converted_not_relabelled(monkeypatch):
    from datetime import datetime, timezone

    index = pd.to_datetime(["2026-11-06"]).tz_localize("Europe/Istanbul")  # gün başı İstanbul = 21:00 UTC önceki gün

    class FakeTicker:
        fast_info = {}
        info = {}

        def history(self, **_kwargs):
            return pd.DataFrame({"Close": [42.5]}, index=index)

    monkeypatch.setattr(
        "src.infrastructure.market_data.yfinance_price_lookup_provider.yf.Ticker",
        lambda _ticker: FakeTicker(),
    )
    snapshot = YFinancePriceLookupProvider().lookup("THYAO.IS")

    assert snapshot.last_close_as_of == datetime(2026, 11, 5, 21, 0, tzinfo=timezone.utc)
