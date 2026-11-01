"""YFinanceAssetPriceProvider: ayrıştırma saf fonksiyonları ve sahte `yf.download` ile sağlayıcı (gerçek ağ yok)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from src.domain.exceptions import MarketDataUnavailableError
from src.infrastructure.market_data import yfinance_asset_price_provider as module
from src.infrastructure.market_data.yfinance_asset_price_provider import (
    YFinanceAssetPriceProvider,
    daily_closes_from_download,
    latest_quotes_from_download,
)

D = Decimal


def multi_frame(closes_by_symbol: dict, index) -> pd.DataFrame:
    columns = pd.MultiIndex.from_product([list(closes_by_symbol), ["Close"]])
    values = np.column_stack(list(closes_by_symbol.values()))
    return pd.DataFrame(values, index=index, columns=columns)


def column_frame(symbol: str, closes, index) -> pd.DataFrame:
    """Varsayılan `yf.download(sembol)` düzeni: sütunlar (alan, sembol), örn. ("Close", "GC=F")."""
    columns = pd.MultiIndex.from_product([["Close"], [symbol]])
    return pd.DataFrame(np.array(closes, dtype=float).reshape(-1, 1), index=index, columns=columns)


class TestLatestQuotes:
    def test_reads_last_valid_close_per_symbol_in_utc(self):
        index = pd.DatetimeIndex(["2026-01-05 14:30", "2026-01-05 14:31"], tz="America/New_York")
        data = multi_frame({"AAPL": [190.0, 191.5], "BTC-USD": [65000.0, np.nan]}, index)

        quotes = latest_quotes_from_download(data, ["AAPL", "BTC-USD"], 7)

        assert quotes["AAPL"].price == D("191.5")
        assert quotes["BTC-USD"].price == D("65000")   # son NaN atlanır
        assert quotes["AAPL"].as_of == datetime(2026, 1, 5, 19, 31)  # 14:31 ET = 19:31 UTC, saat dilimsiz

    def test_float32_noise_is_rounded_away(self):
        index = pd.DatetimeIndex(["2026-01-05 10:00"], tz="UTC")
        data = multi_frame({"X": [float(np.float32(0.98))]}, index)

        assert latest_quotes_from_download(data, ["X"], 7)["X"].price == D("0.9800000")

    def test_small_crypto_prices_keep_precision(self):
        index = pd.DatetimeIndex(["2026-01-05 10:00"], tz="UTC")
        data = multi_frame({"SHIB-USD": [0.00001234]}, index)

        assert latest_quotes_from_download(data, ["SHIB-USD"], 7)["SHIB-USD"].price == D("0.00001234000")

    def test_single_symbol_flat_frame(self):
        index = pd.DatetimeIndex(["2026-01-05"], tz="UTC")
        data = pd.DataFrame({"Close": [2650.25]}, index=index)

        assert latest_quotes_from_download(data, ["GC=F"], 12)["GC=F"].price == D("2650.25")

    def test_missing_symbol_zero_and_empty_are_skipped(self):
        index = pd.DatetimeIndex(["2026-01-05"], tz="UTC")
        data = multi_frame({"A": [0.0], "B": [np.nan]}, index)

        assert latest_quotes_from_download(data, ["A", "B", "C"], 7) == {}
        assert latest_quotes_from_download(pd.DataFrame(), ["A"], 7) == {}
        assert latest_quotes_from_download(None, ["A"], 7) == {}


class TestDailyCloses:
    def test_float32_noise_in_daily_close_is_rounded_away(self):
        index = pd.DatetimeIndex(["2026-10-30"])
        data = column_frame("GC=F", [float(np.float32(3898.9))], index)

        assert daily_closes_from_download(data, "GC=F") == [(date(2026, 10, 30), D("3898.9000"))]

    def test_multiindex_single_symbol_download(self):
        index = pd.DatetimeIndex(["2026-01-02", "2026-01-05", "2026-01-06"])
        data = column_frame("GC=F", [2600.0, np.nan, 2620.5], index)

        assert daily_closes_from_download(data, "GC=F") == [(date(2026, 1, 2), D("2600")), (date(2026, 1, 6), D("2620.5"))]

    def test_flat_frame_and_empty(self):
        data = pd.DataFrame({"Close": [10.0, 11.0]}, index=pd.DatetimeIndex(["2026-01-02", "2026-01-03"]))

        assert [p[0] for p in daily_closes_from_download(data, "X")] == [date(2026, 1, 2), date(2026, 1, 3)]
        assert daily_closes_from_download(pd.DataFrame(), "X") == []


class TestProvider:
    def test_get_latest_falls_back_to_daily_when_market_closed(self, monkeypatch):
        calls = []

        def fake_download(tickers, **kwargs):
            calls.append((tickers, kwargs["period"], kwargs["interval"]))
            if kwargs["interval"] == "1m":
                return pd.DataFrame()
            index = pd.DatetimeIndex(["2026-01-09"], tz="UTC")
            return multi_frame({"AAPL": [190.0], "BTC-USD": [65000.0]}, index)

        monkeypatch.setattr(module.yf, "download", fake_download)

        quotes = YFinanceAssetPriceProvider().get_latest(["AAPL", "BTC-USD", "AAPL"])

        assert set(quotes) == {"AAPL", "BTC-USD"}
        assert calls == [("AAPL BTC-USD", "1d", "1m"), ("AAPL BTC-USD", "5d", "1d")]

    def test_get_latest_returns_empty_when_provider_fails(self, monkeypatch):
        def failing(*args, **kwargs):
            raise OSError("ağ yok")

        monkeypatch.setattr(module.yf, "download", failing)
        monkeypatch.setattr("src.infrastructure.retry._sleep", lambda seconds: None)

        assert YFinanceAssetPriceProvider().get_latest(["AAPL"]) == {}

    def test_get_latest_without_symbols_makes_no_call(self, monkeypatch):
        monkeypatch.setattr(module.yf, "download", lambda *a, **k: pytest.fail("çağrılmamalı"))

        assert YFinanceAssetPriceProvider().get_latest([]) == {}

    def test_get_history_filters_to_requested_range(self, monkeypatch):
        index = pd.DatetimeIndex(["2026-01-01", "2026-01-02", "2026-01-03"])
        monkeypatch.setattr(module.yf, "download", lambda *a, **k: column_frame("GC=F", [1.0, 2.0, 3.0], index))

        history = YFinanceAssetPriceProvider().get_history("GC=F", date(2026, 1, 2), date(2026, 1, 3))

        assert history == [(date(2026, 1, 2), D("2")), (date(2026, 1, 3), D("3"))]

    def test_get_history_wraps_provider_errors(self, monkeypatch):
        def failing(*args, **kwargs):
            raise OSError("ağ yok")

        monkeypatch.setattr(module.yf, "download", failing)
        monkeypatch.setattr("src.infrastructure.retry._sleep", lambda seconds: None)

        with pytest.raises(MarketDataUnavailableError):
            YFinanceAssetPriceProvider().get_history("GC=F", date(2026, 1, 1), date(2026, 1, 2))

    def test_get_history_rejects_inverted_range(self):
        with pytest.raises(ValueError):
            YFinanceAssetPriceProvider().get_history("GC=F", date(2026, 1, 3), date(2026, 1, 2))

    def test_verify_true_when_closes_exist_false_when_empty(self, monkeypatch):
        index = pd.DatetimeIndex(["2026-01-02"])
        monkeypatch.setattr(module.yf, "download", lambda *a, **k: column_frame("AAPL", [190.0], index))
        assert YFinanceAssetPriceProvider().verify("AAPL") is True

        monkeypatch.setattr(module.yf, "download", lambda *a, **k: pd.DataFrame())
        assert YFinanceAssetPriceProvider().verify("ZZZZ") is False

    def test_verify_raises_when_source_unreachable(self, monkeypatch):
        def failing(*args, **kwargs):
            raise OSError("ağ yok")

        monkeypatch.setattr(module.yf, "download", failing)
        monkeypatch.setattr("src.infrastructure.retry._sleep", lambda seconds: None)

        with pytest.raises(MarketDataUnavailableError):
            YFinanceAssetPriceProvider().verify("AAPL")
