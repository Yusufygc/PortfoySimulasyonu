from datetime import date
from decimal import Decimal

import pytest

from src.domain.exceptions import MarketDataUnavailableError
from src.infrastructure.market_data.scraped_benchmark_provider import ScrapedBenchmarkProvider


def test_request_json_wraps_invalid_json_as_market_data_unavailable(monkeypatch):
    provider = ScrapedBenchmarkProvider()
    monkeypatch.setattr(provider, "_request_text", lambda _url: "not-json")

    with pytest.raises(MarketDataUnavailableError, match="JSON"):
        provider._request_json("https://example.test/data")


def test_tcmb_deposit_rates_use_manual_fallback_when_evds_unavailable(monkeypatch):
    class FailingEvdsClient:
        def request_json_post_path(self, *_args, **_kwargs):
            raise MarketDataUnavailableError("evds unavailable")

    provider = ScrapedBenchmarkProvider()
    provider._evds_client = FailingEvdsClient()
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    monkeypatch.setattr(
        provider,
        "_manual_tcmb_deposit_fallback",
        lambda fallback_start: {fallback_start: Decimal("45.0")},
    )

    assert provider._fetch_tcmb_try_deposit_3m_rates(start_date, end_date) == {
        start_date: Decimal("45.0")
    }


# ---------------------------------------------------------------------------
# Hata aileleri ve ayrıştırma (ağ çağrısı yok)
# ---------------------------------------------------------------------------

def test_request_text_maps_url_errors_to_market_data_unavailable(monkeypatch):
    import urllib.error

    from src.infrastructure.market_data import scraped_benchmark_provider as module

    def refuse(request, timeout=None):
        raise urllib.error.URLError("bağlantı reddedildi")

    monkeypatch.setattr(module, "urlopen", refuse)

    with pytest.raises(MarketDataUnavailableError, match="erisilemiyor"):
        ScrapedBenchmarkProvider()._request_text("https://example.test/x")


def test_bist_month_parses_rows_and_skips_bad_values(monkeypatch):
    html = (
        "<tr><td>01/05/2026</td><td>10,250.50</td></tr>"
        "<tr><td>01/06/2026</td><td>10,300.00</td></tr>"
        "<tr><td>13/45/2026</td><td>1.0</td></tr>"
    )
    provider = ScrapedBenchmarkProvider()
    monkeypatch.setattr(provider, "_request_text", lambda url: html)

    series = provider.fetch_series_for_ticker("XU100.IS", date(2026, 1, 1), date(2026, 1, 31))

    assert series == {date(2026, 1, 5): Decimal("10250.50"), date(2026, 1, 6): Decimal("10300.00")}


def test_bist_month_fetch_failure_returns_empty_and_is_cached_for_the_instance(monkeypatch):
    provider = ScrapedBenchmarkProvider()
    calls = []

    def failing(url):
        calls.append(url)
        raise MarketDataUnavailableError("kapalı")

    monkeypatch.setattr(provider, "_request_text", failing)

    first = provider.fetch_series_for_ticker("^XU100", date(2026, 1, 1), date(2026, 1, 31))
    second = provider.fetch_series_for_ticker("^XU100", date(2026, 1, 1), date(2026, 1, 31))

    assert first == {} and second == {}
    assert len(calls) == 1  # başarısızlık örnek ömrü boyunca önbellekte kalır (yeniden deneme yok)


def test_gold_try_series_multiplies_gold_by_usd_try_on_shared_dates_only(monkeypatch):
    provider = ScrapedBenchmarkProvider()
    # 2026-01-05 ve 2026-01-06 UTC gece yarısı (ms)
    payload = {"data": [[1767571200000, 2000.0], [1767657600000, 2010.0], [1767744000000, None], "bozuk"]}
    monkeypatch.setattr(provider, "_request_json", lambda url: payload)
    monkeypatch.setattr(provider, "_fetch_exchange_rates_usdtry_series",
                        lambda s, e: {date(2026, 1, 5): Decimal("40"), date(2026, 1, 9): Decimal("41")})

    series = provider.fetch_series_for_ticker("XAUTRY=X", date(2026, 1, 1), date(2026, 1, 31))

    assert series == {date(2026, 1, 5): Decimal("80000.0")}


def test_unknown_ticker_has_no_scraped_series():
    assert ScrapedBenchmarkProvider().fetch_series_for_ticker("THYAO", date(2026, 1, 1), date(2026, 1, 31)) is None
