from datetime import date
from decimal import Decimal

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("yfinance")

from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient


def test_get_price_series_uses_countryeconomy_for_bist_without_yfinance(monkeypatch):
    client = YFinanceMarketDataClient()
    calls = []
    bist_html = """
        <table>
            <tr><td>01/01/2026</td><td>12,345.67</td><td>0.10%</td></tr>
            <tr><td>01/02/2026</td><td>12,400.01</td><td>0.44%</td></tr>
        </table>
    """

    def fake_request_text(url):
        calls.append(url)
        return bist_html

    monkeypatch.setattr(client, "_request_text", fake_request_text)
    monkeypatch.setattr(
        client,
        "_download_dataframe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("yfinance cagrilmamaliydi")),
    )
    monkeypatch.setattr(
        client,
        "_request_to_investing",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Investing fallback cagrilmamaliydi")),
    )

    series = client.get_price_series("XU100.IS", date(2026, 1, 1), date(2026, 1, 2))

    assert series == {
        date(2026, 1, 1): Decimal("12345.67"),
        date(2026, 1, 2): Decimal("12400.01"),
    }
    assert calls == ["https://countryeconomy.com/stock-exchange/turkey?dr=2026-01"]


def test_get_price_series_uses_exchange_rates_for_usdtry_without_yfinance(monkeypatch):
    client = YFinanceMarketDataClient()
    year_html = """
        <tr>
            <td>
                <a href="/exchange-rate-history/usd-try-2026-01-01" class="w">January 1, 2026</a>
                <a href="/exchange-rate-history/usd-try-2026-01-01" class="n">2026-1-1</a>
            </td>
            <td>
                <span class="w"><span class="nowrap">1 USD =</span> <span class="nowrap">42.971 TRY</span></span>
            </td>
        </tr>
        <tr>
            <td>
                <a href="/exchange-rate-history/usd-try-2026-01-02" class="w">January 2, 2026</a>
                <a href="/exchange-rate-history/usd-try-2026-01-02" class="n">2026-1-2</a>
            </td>
            <td>
                <span class="w"><span class="nowrap">1 USD =</span> <span class="nowrap">43.038 TRY</span></span>
            </td>
        </tr>
    """

    monkeypatch.setattr(client, "_request_text", lambda url: year_html)
    monkeypatch.setattr(
        client,
        "_download_dataframe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("yfinance cagrilmamaliydi")),
    )
    monkeypatch.setattr(
        client,
        "_request_to_investing",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Investing fallback cagrilmamaliydi")),
    )

    series = client.get_price_series("TRY=X", date(2026, 1, 1), date(2026, 1, 2))

    assert series == {
        date(2026, 1, 1): Decimal("42.971"),
        date(2026, 1, 2): Decimal("43.038"),
    }


def test_get_price_series_builds_xautry_from_gold_and_usd_sources(monkeypatch):
    client = YFinanceMarketDataClient()
    gold_payload = {
        "data": [
            [int(pd.Timestamp("2026-01-01", tz="UTC").timestamp() * 1000), 100],
            [int(pd.Timestamp("2026-01-02", tz="UTC").timestamp() * 1000), 101.5],
        ]
    }
    year_html = """
        <tr>
            <td>
                <a href="/exchange-rate-history/usd-try-2026-01-01" class="w">January 1, 2026</a>
                <a href="/exchange-rate-history/usd-try-2026-01-01" class="n">2026-1-1</a>
            </td>
            <td>
                <span class="w"><span class="nowrap">1 USD =</span> <span class="nowrap">43.000 TRY</span></span>
            </td>
        </tr>
        <tr>
            <td>
                <a href="/exchange-rate-history/usd-try-2026-01-02" class="w">January 2, 2026</a>
                <a href="/exchange-rate-history/usd-try-2026-01-02" class="n">2026-1-2</a>
            </td>
            <td>
                <span class="w"><span class="nowrap">1 USD =</span> <span class="nowrap">44.000 TRY</span></span>
            </td>
        </tr>
    """

    def fake_request_text(url):
        if "exchange-rates.org" in url:
            return year_html
        raise AssertionError(f"Beklenmeyen text istegi: {url}")

    def fake_request_json(url):
        if "macrotrends.net/economic-data/2627/D" in url:
            return gold_payload
        raise AssertionError(f"Beklenmeyen json istegi: {url}")

    monkeypatch.setattr(client, "_request_text", fake_request_text)
    monkeypatch.setattr(client, "_request_json", fake_request_json)
    monkeypatch.setattr(
        client,
        "_download_dataframe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("yfinance cagrilmamaliydi")),
    )
    monkeypatch.setattr(
        client,
        "_request_to_investing",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Investing fallback cagrilmamaliydi")),
    )

    series = client.get_price_series("XAUTRY=X", date(2026, 1, 1), date(2026, 1, 2))

    assert series == {
        date(2026, 1, 1): Decimal("4300.0"),
        date(2026, 1, 2): Decimal("4466.0"),
    }


def test_countryeconomy_month_cache_is_reused(monkeypatch):
    client = YFinanceMarketDataClient()
    counter = {"count": 0}
    bist_html = "<tr><td>01/01/2026</td><td>12,345.67</td><td>0.10%</td></tr>"

    def fake_request_text(url):
        counter["count"] += 1
        return bist_html

    monkeypatch.setattr(client, "_request_text", fake_request_text)
    monkeypatch.setattr(
        client,
        "_download_dataframe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("yfinance cagrilmamaliydi")),
    )

    first = client.get_price_series("XU100.IS", date(2026, 1, 1), date(2026, 1, 1))
    second = client.get_price_series("XU100.IS", date(2026, 1, 1), date(2026, 1, 1))

    assert first == second == {date(2026, 1, 1): Decimal("12345.67")}
    assert counter["count"] == 1
