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
