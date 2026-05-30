from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from src.application.services.market.price_lookup_service import PriceLookupService


class FakeTicker:
    fast_info = {}
    info = {}
    history_frame = pd.DataFrame()
    history_calls = []

    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, **kwargs):
        self.history_calls.append(kwargs)
        return self.history_frame


def test_price_lookup_normalizes_ticker_and_returns_company_name_for_intraday(monkeypatch):
    FakeTicker.fast_info = {"lastPrice": 401.75}
    FakeTicker.info = {"longName": "Aselsan Elektronik Sanayi ve Ticaret A.S."}
    FakeTicker.history_frame = pd.DataFrame()
    FakeTicker.history_calls = []
    captured = []

    def ticker_factory(ticker):
        captured.append(ticker)
        return FakeTicker(ticker)

    monkeypatch.setattr("src.application.services.market.price_lookup_service.yf.Ticker", ticker_factory)

    result = PriceLookupService().lookup_price_for_ticker("asels")

    assert captured == ["ASELS.IS"]
    assert result.price == Decimal("401.75")
    assert result.source == "intraday"
    assert result.company_name == "Aselsan Elektronik Sanayi ve Ticaret A.S."
    assert result.normalized_ticker == "ASELS.IS"
    assert FakeTicker.history_calls == []


def test_price_lookup_uses_last_close_with_latest_returned_history_date(monkeypatch):
    FakeTicker.fast_info = {}
    FakeTicker.info = {"shortName": "ASELSAN"}
    FakeTicker.history_frame = pd.DataFrame(
        {"Close": [Decimal("398.10"), Decimal("401.75")]},
        index=pd.to_datetime(["2026-05-25", "2026-05-26"]),
    )
    FakeTicker.history_calls = []
    monkeypatch.setattr("src.application.services.market.price_lookup_service.yf.Ticker", FakeTicker)

    result = PriceLookupService().lookup_price_for_ticker("ASELS.IS")

    assert result.price == Decimal("401.75")
    assert result.source == "last_close"
    assert result.company_name == "ASELSAN"
    assert result.normalized_ticker == "ASELS.IS"
    assert result.as_of == datetime(2026, 5, 26, tzinfo=timezone.utc)
    assert FakeTicker.history_calls == [{"period": "7d", "auto_adjust": False}]
