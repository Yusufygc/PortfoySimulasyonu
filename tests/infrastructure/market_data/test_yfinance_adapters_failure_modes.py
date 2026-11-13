"""yfinance tabanlı adaptörler: ağ çağrısı yapmadan başarı, boş yanıt ve hata ailesi davranışları."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.infrastructure.market_data import yfinance_bist_bar_downloader as bars_module
from src.infrastructure.market_data import yfinance_optimization_market_data_provider as opt_module
from src.infrastructure.retry import DEFAULT_ATTEMPTS


def _single_frame(rows):
    index = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {"Open": [r[1] for r in rows], "High": [r[2] for r in rows], "Low": [r[3] for r in rows],
         "Close": [r[4] for r in rows], "Volume": [r[5] for r in rows]},
        index=pd.Index(index, name="Date"),
    )


# ---------------------------------------------------------------- BIST bar indirici

def test_bar_downloader_single_ticker_skips_rows_without_valid_close(monkeypatch):
    frame = _single_frame([("2026-01-05", 10, 11, 9, 10.5, 1000), ("2026-01-06", 10, 11, 9, 0, 500),
                           ("2026-01-07", 10, 12, 9, 11.0, float("nan"))])
    monkeypatch.setattr(bars_module.yf, "download", lambda *a, **k: frame)

    bars, updated, errors = bars_module.YFinanceBistBarDownloader().download_daily(
        ["THYAO"], date(2026, 1, 1), date(2026, 1, 10))

    assert [b.price_date for b in bars] == [date(2026, 1, 5), date(2026, 1, 7)]
    assert bars[1].volume == 0 and updated == 1 and errors == []


def test_bar_downloader_batch_error_is_reported_and_other_chunks_continue(monkeypatch):
    calls = []

    def fake_download(symbols, **kwargs):
        calls.append(symbols)
        if len(calls) == 1:
            raise RuntimeError("429 Too Many Requests")
        return _single_frame([("2026-01-05", 1, 2, 1, 1.5, 10)])

    monkeypatch.setattr(bars_module.yf, "download", fake_download)
    tickers = [f"T{i:03d}" for i in range(bars_module.CHUNK_SIZE)] + ["LAST"]

    bars, updated, errors = bars_module.YFinanceBistBarDownloader().download_daily(
        tickers, date(2026, 1, 1), date(2026, 1, 10))

    assert len(calls) == 2 and updated == 1 and bars[0].ticker == "LAST"
    assert len(errors) == 1 and "blok 0" in errors[0] and "429" in errors[0]


def test_bar_downloader_empty_response_yields_nothing(monkeypatch):
    monkeypatch.setattr(bars_module.yf, "download", lambda *a, **k: pd.DataFrame())

    assert bars_module.YFinanceBistBarDownloader().download_daily(
        ["THYAO"], date(2026, 1, 1), date(2026, 1, 10)) == ([], 0, [])


def test_bar_downloader_multi_ticker_frame_drops_missing_symbols(monkeypatch):
    first = _single_frame([("2026-01-05", 1, 2, 1, 1.5, 10)])
    data = pd.concat({"AAA.IS": first}, axis=1)
    monkeypatch.setattr(bars_module.yf, "download", lambda *a, **k: data)

    bars, updated, _ = bars_module.YFinanceBistBarDownloader().download_daily(
        ["AAA", "BBB"], date(2026, 1, 1), date(2026, 1, 10))

    assert [b.ticker for b in bars] == ["AAA"] and updated == 1


# ---------------------------------------------------------------- optimizasyon verisi

def _close_frame(columns, days=70):
    index = pd.date_range("2025-10-01", periods=days, freq="D")
    data = {col: [100 + i for i in range(days)] for col in columns}
    return pd.concat({"Close": pd.DataFrame(data, index=index)}, axis=1)


def test_optimization_provider_maps_yf_symbols_back_to_canonical_tickers(monkeypatch):
    monkeypatch.setattr(opt_module.yf, "download", lambda **kw: _close_frame(["THYAO.IS", "ASELS.IS"]))

    frame = opt_module.YFinanceOptimizationMarketDataProvider().get_historical_prices(["THYAO", "ASELS"], 90)

    assert list(frame.columns) == ["THYAO", "ASELS"] and len(frame) == 70


def test_optimization_provider_drops_columns_with_less_than_60_points(monkeypatch):
    data = _close_frame(["THYAO.IS", "ASELS.IS"])
    data[("Close", "ASELS.IS")] = [float("nan")] * 20 + [1.0] * 50
    monkeypatch.setattr(opt_module.yf, "download", lambda **kw: data)

    frame = opt_module.YFinanceOptimizationMarketDataProvider().get_historical_prices(["THYAO", "ASELS"], 90)

    assert list(frame.columns) == ["THYAO"]


def test_optimization_provider_empty_download_returns_empty_frame(monkeypatch):
    monkeypatch.setattr(opt_module.yf, "download", lambda **kw: pd.DataFrame())

    assert opt_module.YFinanceOptimizationMarketDataProvider().get_historical_prices(["THYAO"], 90).empty


def test_optimization_provider_wraps_transient_failures_after_retries(monkeypatch):
    attempts = []

    def failing(**kw):
        attempts.append(1)
        raise ConnectionError("ağ yok")

    monkeypatch.setattr(opt_module.yf, "download", failing)

    with pytest.raises(ValueError, match="Fiyat verisi cekilemedi"):
        opt_module.YFinanceOptimizationMarketDataProvider().get_historical_prices(["THYAO"], 90)

    assert len(attempts) == DEFAULT_ATTEMPTS


def test_last_price_prefers_fast_info_then_history_and_swallows_data_errors(monkeypatch):
    class Ticker:
        fast_info = {"lastPrice": 301.5}

    monkeypatch.setattr(opt_module.yf, "Ticker", lambda symbol: Ticker())
    provider = opt_module.YFinanceOptimizationMarketDataProvider()
    assert provider.get_last_price("THYAO") == 301.5

    class Broken:
        @property
        def fast_info(self):
            raise ConnectionError("kapalı")

    monkeypatch.setattr(opt_module.yf, "Ticker", lambda symbol: Broken())
    assert provider.get_last_price("THYAO") is None
