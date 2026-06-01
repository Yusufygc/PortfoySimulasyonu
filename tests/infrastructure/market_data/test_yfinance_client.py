import pandas as pd
from datetime import date
from decimal import Decimal
import pytest
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient

def test_get_closing_price_success(monkeypatch):
    client = YFinanceMarketDataClient()
    
    # Create dummy dataframe representing a yfinance response
    df = pd.DataFrame({"Close": [10.5]}, index=[pd.Timestamp("2026-01-01")])
    
    download_calls = []
    def mock_download(tickers, start, end):
        download_calls.append((tickers, start, end))
        return df
        
    monkeypatch.setattr(client, "_download_dataframe", mock_download)
    
    price = client.get_closing_price(1, "AAPL", date(2026, 1, 1))
    assert price == Decimal("10.5")
    assert len(download_calls) == 1
    assert download_calls[0] == ("AAPL", date(2026, 1, 1), date(2026, 1, 2))

def test_get_closing_price_empty_response(monkeypatch):
    client = YFinanceMarketDataClient()
    df = pd.DataFrame()
    
    monkeypatch.setattr(client, "_download_dataframe", lambda *a: df)
    
    with pytest.raises(ValueError, match="AAPL icin 2026-01-01 gun sonu fiyati bulunamadi"):
        client.get_closing_price(1, "AAPL", date(2026, 1, 1))

def test_get_closing_prices_multi_ticker(monkeypatch):
    client = YFinanceMarketDataClient()
    
    # yfinance returns multi-index columns for multi-ticker download
    columns = pd.MultiIndex.from_tuples([("Close", "AAPL"), ("Close", "MSFT")])
    df = pd.DataFrame([[150.0, 400.0]], index=[pd.Timestamp("2026-01-01")], columns=columns)
    
    download_calls = []
    def mock_download(tickers, start, end):
        download_calls.append((tickers, start, end))
        return df
        
    monkeypatch.setattr(client, "_download_dataframe", mock_download)
    
    prices = client.get_closing_prices([1, 2], ["AAPL", "MSFT"], date(2026, 1, 1))
    assert prices == {1: Decimal("150.0"), 2: Decimal("400.0")}
    assert download_calls[0][0] == ["AAPL", "MSFT"]

def test_get_price_series(monkeypatch):
    client = YFinanceMarketDataClient()
    
    df = pd.DataFrame({"Close": [100.0, 101.5, 102.0]}, 
                      index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]))
                      
    download_calls = []
    def mock_download(tickers, start, end):
        download_calls.append((tickers, start, end))
        return df
        
    monkeypatch.setattr(client, "_download_dataframe", mock_download)
    
    series = client.get_price_series("AAPL", date(2026, 1, 1), date(2026, 1, 3))
    assert series == {
        date(2026, 1, 1): Decimal("100.0"),
        date(2026, 1, 2): Decimal("101.5"),
        date(2026, 1, 3): Decimal("102.0"),
    }
