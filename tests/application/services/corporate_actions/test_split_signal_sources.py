from datetime import date, timedelta
from decimal import Decimal as D
from types import SimpleNamespace as NS

import pandas as pd
import pytest
from yfinance.exceptions import YFException

from src.application.services.corporate_actions.split_signal_sources import (
    CompositeSplitSignalSource,
    KapSplitSignalSource,
    PriceBreakSplitSignalSource,
)
from src.domain.models.corporate_action import ActionType
from src.domain.models.split_signal import SplitSource
from src.domain.ports.services.i_corporate_action_provider import CorporateActionProviderUnavailable
from src.domain.ports.services.i_split_signal_provider import ISplitSignalProvider, SplitTarget
from src.domain.split_detection import persistent_breaks, persistent_steps
from src.infrastructure.corporate_actions.yahoo_split_provider import YahooSplitProvider

SDTTR = SplitTarget("SDTTR", "SDTTR.IS", stock_id=79)
TODAY = date(2026, 9, 10)


def _days(start: date, n: int):
    return [start + timedelta(days=i) for i in range(n)]


# ----------------------------------------------------------------- saf tespit


def test_persistent_step_finds_unadjusted_history_against_adjusted_source():
    days = _days(date(2026, 8, 14), 10)
    ratios = [(d, 11.0) for d in days[:5]] + [(d, 1.0) for d in days[5:]]
    assert persistent_steps(ratios) == [(days[5], 11.0)]


def test_dividend_sized_step_is_ignored():
    days = _days(date(2026, 1, 1), 10)
    ratios = [(d, 1.05) for d in days[:5]] + [(d, 1.0) for d in days[5:]]
    assert persistent_steps(ratios) == []


def test_persistent_break_requires_new_level_to_hold():
    days = _days(date(2026, 1, 1), 8)
    split = [(d, 100.0) for d in days[:4]] + [(d, 50.0) for d in days[4:]]
    glitch = [(d, 100.0) for d in days[:4]] + [(days[4], 50.0)] + [(d, 100.0) for d in days[5:]]
    assert persistent_breaks(split) == [(days[4], 2.0)]
    assert persistent_breaks(glitch) == []


def test_limit_down_day_is_not_a_break():
    days = _days(date(2026, 1, 1), 8)
    closes = [(d, 100.0) for d in days[:4]] + [(d, 90.0) for d in days[4:]]  # BIST %10 taban
    assert persistent_breaks(closes) == []


# ----------------------------------------------------------------- Yahoo


def test_yahoo_provider_maps_splits_after_since():
    index = pd.to_datetime(["2020-01-02 09:30", "2026-08-27 09:30"]).tz_localize("Europe/Istanbul")
    series = pd.Series([2.0, 11.000000000000002], index=index)
    signals = YahooSplitProvider(fetcher=lambda _sym: series).fetch_signals([SDTTR], date(2025, 1, 1))
    assert [(s.ticker, s.ex_date, s.multiplier, s.source) for s in signals] == [
        ("SDTTR", date(2026, 8, 27), D("11.0"), SplitSource.YAHOO)
    ]


def test_yahoo_provider_skips_failing_symbol():
    def fetcher(_sym):
        raise YFException("down")

    assert YahooSplitProvider(fetcher=fetcher).fetch_signals([SDTTR], date(2025, 1, 1)) == []


# ----------------------------------------------------------------- KAP


class _Kap:
    def __init__(self, candidates=None, error=None):
        self._candidates, self._error = candidates or [], error

    def fetch_candidates(self, tickers, start_date=None, end_date=None):
        if self._error:
            raise self._error
        return self._candidates


def _candidate(ticker, action_type, ratio, ex_date):
    return NS(ticker=ticker, action_type=action_type, ratio=ratio, ex_date=ex_date,
              source_url="https://kap.org.tr/x", source_disclosure_id="1")


def test_kap_bedelsiz_becomes_signal_and_bedelli_is_ignored():
    kap = _Kap([
        _candidate("SDTTR", ActionType.BEDELSIZ, D("10"), date(2026, 8, 21)),
        _candidate("SDTTR", ActionType.BEDELLI, D("1"), date(2026, 8, 21)),
        _candidate("OTHER", ActionType.BEDELSIZ, D("1"), date(2026, 8, 21)),
    ])
    signals = KapSplitSignalSource(kap).fetch_signals([SDTTR], date(2026, 1, 1))
    assert [(s.ticker, s.multiplier, s.source) for s in signals] == [("SDTTR", D("11"), SplitSource.KAP)]


def test_kap_unavailable_returns_empty():
    kap = _Kap(error=CorporateActionProviderUnavailable("404"))
    assert KapSplitSignalSource(kap).fetch_signals([SDTTR], date(2026, 1, 1)) == []


# ----------------------------------------------------------------- fiyat kırılması


class _History:
    def __init__(self, raw, adjusted):
        self._raw, self._adjusted = raw, adjusted

    def get_price_series(self, ticker, start, end, adjusted=True):
        data = self._adjusted if adjusted else self._raw
        return [NS(price_date=d, close_price=c) for d, c in data if start <= d <= end]


class _Prices:
    def __init__(self, closes):
        self._closes = closes

    def get_price_series(self, stock_id, start, end):
        return [NS(price_date=d, close_price=D(str(c))) for d, c in self._closes if start <= d <= end]


@pytest.fixture
def frozen_today(monkeypatch):
    monkeypatch.setattr("src.application.services.corporate_actions.split_signal_sources.market_today", lambda: TODAY)


def test_sqlite_unadjusted_history_against_yahoo_adjusted_duckdb(frozen_today):
    days = _days(date(2026, 8, 14), 10)
    adjusted = [(d, 23.0) for d in days]                                   # Yahoo geçmişi bölünmeye göre düzeltti
    stored = [(d, 253.0) for d in days[:5]] + [(d, 23.0) for d in days[5:]]  # SQLite eski ham fiyatı tutuyor
    source = PriceBreakSplitSignalSource(_History(adjusted, adjusted), _Prices(stored))
    [signal] = source.fetch_signals([SDTTR], date(2026, 8, 1))
    assert (signal.ex_date, signal.multiplier, signal.source) == (days[5], D("11.0000"), SplitSource.PRICE_BREAK)


def test_raw_duckdb_break_is_reported(frozen_today):
    days = _days(date(2026, 8, 14), 10)
    raw = [(d, 100.0) for d in days[:5]] + [(d, 25.0) for d in days[5:]]
    adjusted = [(d, 25.0) for d in days]
    stored = [(d, 25.0) for d in days]  # SQLite zaten düzeltilmiş
    [signal] = PriceBreakSplitSignalSource(_History(raw, adjusted), _Prices(stored)).fetch_signals([SDTTR], date(2026, 8, 1))
    assert (signal.ex_date, signal.multiplier) == (days[5], D("4.0000"))


def test_targets_without_stock_id_are_skipped(frozen_today):
    source = PriceBreakSplitSignalSource(_History([], []), _Prices([]))
    assert source.fetch_signals([SplitTarget("AAPL", "AAPL", asset_id=3)], date(2026, 1, 1)) == []


# ----------------------------------------------------------------- birleşik


def test_composite_keeps_other_sources_when_one_fails():
    class Boom(ISplitSignalProvider):
        def fetch_signals(self, targets, since):
            raise RuntimeError("boom")

    index = pd.to_datetime(["2026-08-27"])
    yahoo = YahooSplitProvider(fetcher=lambda _s: pd.Series([11.0], index=index))
    signals = CompositeSplitSignalSource([Boom(), yahoo]).fetch_signals([SDTTR], date(2026, 1, 1))
    assert [s.source for s in signals] == [SplitSource.YAHOO]


def test_one_ticker_read_error_does_not_stop_others(frozen_today):
    days = _days(date(2026, 8, 14), 10)
    raw = [(d, 100.0) for d in days[:5]] + [(d, 25.0) for d in days[5:]]

    class History(_History):
        def get_price_series(self, ticker, start, end, adjusted=True):
            if ticker == "BAD":
                raise OSError("duckdb locked")
            return super().get_price_series(ticker, start, end, adjusted)

    source = PriceBreakSplitSignalSource(History(raw, []), _Prices([]))
    signals = source.fetch_signals([SplitTarget("BAD", "BAD.IS", 1), SDTTR], date(2026, 8, 1))
    assert [s.ticker for s in signals] == ["SDTTR"]
