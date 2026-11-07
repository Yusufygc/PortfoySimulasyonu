from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.application.services.analysis.benchmark_service import AnalysisBenchmarkService
from src.domain.units import TROY_OUNCE_GRAMS

DEAD_YAHOO_SYMBOLS = {"XAUTRY=X", "XAGTRY=X", "XAUUSD=X", "XAGUSD=X"}


class RecordingMarketClient:
    def __init__(self, series_by_ticker):
        self._series = series_by_ticker
        self.requested = []

    def get_price_series(self, ticker, start_date, end_date):
        self.requested.append(ticker)
        return dict(self._series.get(ticker, {}))


class StubEvds:
    def __init__(self, items):
        self._items = items

    def get_series(self, series_code, start_date, end_date):
        return self._items


D1, D2 = date(2026, 1, 1), date(2026, 1, 2)


@pytest.mark.parametrize(
    "code, futures",
    [("gold", "GC=F"), ("silver", "SI=F")],
)
def test_precious_metal_built_from_futures_times_usdtry_per_gram(code, futures):
    client = RecordingMarketClient({
        futures: {D1: Decimal("2000"), D2: Decimal("2100")},
        "TRY=X": {D1: Decimal("40"), D2: Decimal("41")},
    })
    service = AnalysisBenchmarkService(client)

    series, _ = service.build_benchmark_series(D1, D2, [code])

    assert len(series) == 1
    assert series[0].points == {
        D1: Decimal("2000") * Decimal("40") / TROY_OUNCE_GRAMS,
        D2: Decimal("2100") * Decimal("41") / TROY_OUNCE_GRAMS,
    }
    assert not DEAD_YAHOO_SYMBOLS.intersection(client.requested)
    assert client.requested == [futures, "TRY=X"]


@pytest.mark.parametrize("code", ["gold", "silver"])
def test_benchmark_definitions_do_not_reference_dead_yahoo_symbols(code):
    service = AnalysisBenchmarkService(RecordingMarketClient({}))
    definition = next(d for d in service.get_benchmark_definitions() if d.code == code)
    assert definition.ticker not in DEAD_YAHOO_SYMBOLS


@pytest.mark.parametrize("code, futures", [("gold", "GC=F"), ("silver", "SI=F")])
def test_precious_metal_without_usdtry_is_dropped_with_warning_not_usd_labelled_tl(code, futures):
    client = RecordingMarketClient({futures: {D1: Decimal("2000"), D2: Decimal("2100")}})
    service = AnalysisBenchmarkService(client)

    series, warnings = service.build_benchmark_series(D1, D2, [code])

    assert series == []
    assert any("Veri akışı hatası" in w for w in warnings)


def test_deposit_index_uses_injected_fallback_rate_before_first_published_rate():
    first_rate_day = date(2026, 1, 3)
    evds = StubEvds([{"Tarih": "03-01-2026", "TP_KTF10": "50"}])
    service = AnalysisBenchmarkService(
        RecordingMarketClient({}), evds_client=evds, deposit_rate_fallback=Decimal("36.5")
    )

    series, _ = service.build_benchmark_series(D1, first_rate_day + timedelta(days=1), ["deposit"])

    points = series[0].points
    fallback_growth = Decimal("1") + Decimal("36.5") / Decimal("100") / Decimal("365")
    assert points[D1] == Decimal("100")
    assert points[D2] == Decimal("100") * fallback_growth
    assert points[first_rate_day] == Decimal("100") * fallback_growth * fallback_growth


def test_deposit_index_without_fallback_starts_at_first_published_rate():
    evds = StubEvds([{"Tarih": "02-01-2026", "TP_KTF10": "50"}])
    service = AnalysisBenchmarkService(RecordingMarketClient({}), evds_client=evds)

    series, _ = service.build_benchmark_series(D1, date(2026, 1, 3), ["deposit"])

    points = series[0].points
    assert D1 not in points
    assert points[D2] == Decimal("100")
