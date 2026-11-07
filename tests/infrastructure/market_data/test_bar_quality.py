from datetime import date

from src.infrastructure.market_data.bar_quality import is_flat_zero_volume, is_ghost_bar


def test_holiday_bar_is_ghost_even_with_volume():
    assert is_ghost_bar(date(2026, 5, 27), (10, 11, 9, 10.5, 1000))  # Kurban Bayramı 2026


def test_flat_zero_volume_bar_is_ghost():
    assert is_ghost_bar(date(2025, 5, 8), (7.25, 7.25, 7.25, 7.25, 0))
    assert is_flat_zero_volume((7.25, 7.25, 7.25, 7.25, 0))


def test_real_bar_and_pre_calendar_holiday_are_kept():
    assert not is_ghost_bar(date(2025, 5, 9), (214.7, 226.9, 207.0, 215.4, 3643667))
    assert not is_ghost_bar(date(2016, 7, 15), (10, 11, 9, 10.5, 1000))  # 15 Temmuz 2017 öncesi işlem günü


def test_missing_values_are_not_flat():
    assert not is_flat_zero_volume((None, 1, 1, 1, 0))
    assert not is_flat_zero_volume((float("nan"), 1, 1, 1, 0))


# ----------------------------------------------------------------- indiricilere bağlantı

import pandas as pd  # noqa: E402

GHOST_INDEX = pd.to_datetime(["2026-05-26", "2026-05-27", "2026-06-01", "2026-06-02"]).rename("Date")
GHOST_HIST = pd.DataFrame(
    {
        "Open": [10.0, 10.0, 7.25, 10.2],
        "High": [10.5, 10.0, 7.25, 10.6],
        "Low": [9.8, 10.0, 7.25, 10.1],
        "Close": [10.0, 10.0, 7.25, 10.4],
        "Volume": [1000, 0, 0, 2000],
    },
    index=GHOST_INDEX,  # 26.05 arife (gerçek), 27.05 bayram, 01.06 hacimsiz sabit, 02.06 gerçek
)


def test_bulk_downloader_drops_ghost_bars():
    from src.infrastructure.market_data.bist_bulk_downloader import BistBulkDownloader

    frame = BistBulkDownloader.normalize_history_frame("ASELS", GHOST_HIST)
    assert [str(d) for d in frame["price_date"]] == ["2026-05-26", "2026-06-02"]


def test_incremental_downloader_drops_ghost_bars():
    from src.infrastructure.market_data.yfinance_bist_bar_downloader import _bars_from_frame

    bars = _bars_from_frame("ASELS", GHOST_HIST)
    assert [str(b.price_date) for b in bars] == ["2026-05-26", "2026-06-02"]


def test_price_client_drops_ghost_bars_only_for_bist(monkeypatch):
    from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient

    client = YFinanceMarketDataClient()
    monkeypatch.setattr(client, "_download_dataframe", lambda tickers, start, end: GHOST_HIST)
    bist = client.get_price_series("ASELS", date(2026, 5, 26), date(2026, 6, 2))
    fx = client.get_price_series("TRY=X", date(2026, 5, 26), date(2026, 6, 2))
    assert [str(d) for d in bist] == ["2026-05-26", "2026-06-02"]
    assert len(fx) == 4  # kur ve yabancı semboller BIST takvimine tabi değil
