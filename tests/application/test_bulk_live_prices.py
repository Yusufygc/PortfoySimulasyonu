"""Toplu canlı fiyat: yf.download çıktısının ayrıştırılması, servis eşlemesi ve canlı yenilemenin tekli yola düşmesi (ağ yok)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from src.application.services.market.live_price_refresh_service import LivePriceRefreshService
from src.application.services.market.price_lookup_service import PriceLookupResult, PriceLookupService
from src.infrastructure.market_data.yfinance_price_lookup_provider import latest_bars_from_download


def _download_frame():
    """yfinance 1.x `group_by="ticker"` biçimi: (sembol, alan) çok düzeyli sütunlar, Istanbul saatli dakika indeksi."""
    index = pd.DatetimeIndex(["2026-10-05 11:58", "2026-10-05 11:59"]).tz_localize("Europe/Istanbul")
    columns = pd.MultiIndex.from_product([["AAA.IS", "BBB.IS"], ["Open", "Close"]])
    return pd.DataFrame(
        [[10.0, 10.1, 5.0, float("nan")],
         [10.1, 10.2, 5.0, float("nan")]],
        index=index, columns=columns,
    )


def test_latest_bar_per_symbol_with_utc_timestamp():
    result = latest_bars_from_download(_download_frame(), ["AAA.IS", "BBB.IS", "CCC.IS"])

    assert set(result) == {"AAA.IS"}  # BBB kapanışı boş, CCC indirilmedi
    price, as_of = result["AAA.IS"]
    assert price == Decimal("10.2")
    assert as_of == datetime(2026, 10, 5, 8, 59, tzinfo=timezone.utc)  # 11:59 Istanbul = 08:59 UTC


def test_single_symbol_flat_frame_and_empty_download():
    index = pd.DatetimeIndex(["2026-10-05 08:00"])  # saat dilimsiz: UTC kabul
    flat = pd.DataFrame({"Close": [0.9800000190734863]}, index=index)  # yfinance float32 kalıntısı
    assert latest_bars_from_download(flat, ["AAA.IS"]) == {"AAA.IS": (Decimal("0.98"), datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc))}
    assert latest_bars_from_download(pd.DataFrame(), ["AAA.IS"]) == {}
    assert latest_bars_from_download(None, ["AAA.IS"]) == {}


class _BulkProvider:
    def __init__(self, quotes):
        self.quotes, self.requests = quotes, []

    def lookup(self, normalized_ticker):
        return None

    def lookup_intraday_bulk(self, symbols):
        self.requests.append(list(symbols))
        return {s: q for s, q in self.quotes.items() if s in symbols}


def test_service_maps_bulk_quotes_back_to_given_tickers():
    stamp = datetime(2026, 10, 5, 8, 59, tzinfo=timezone.utc)
    provider = _BulkProvider({"THYAO.IS": (Decimal("300"), stamp)})

    result = PriceLookupService(provider).lookup_prices_bulk(["thyao", "ASELS.IS"])

    assert provider.requests == [["THYAO.IS", "ASELS.IS"]]
    assert set(result) == {"thyao"}
    assert result["thyao"].price == Decimal("300") and result["thyao"].as_of == stamp and result["thyao"].source == "intraday"


def test_service_without_bulk_support_returns_empty():
    class _OnlySingle:
        def lookup(self, normalized_ticker):
            return None

    assert PriceLookupService(_OnlySingle()).lookup_prices_bulk(["THYAO"]) == {}


class _Repo:
    def get_ticker_map_for_stock_ids(self, ids):
        return {1: "AAA.IS", 2: "BBB.IS", 3: "CCC.IS"}


class _Health:
    def active_stock_ids(self, scope=None):
        return {1, 2, 3}


class _Lookup:
    def __init__(self):
        self.single = []

    def lookup_prices_bulk(self, tickers):
        stamp = datetime(2026, 10, 5, 8, 59, tzinfo=timezone.utc)
        return {"AAA.IS": PriceLookupResult(Decimal("10"), stamp, "intraday"), "BBB.IS": PriceLookupResult(Decimal("20"), stamp, "intraday")}

    def lookup_price_for_ticker(self, ticker):
        self.single.append(ticker)
        return PriceLookupResult(Decimal("30"), datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc), "intraday")


class _LatestRepo:
    def __init__(self):
        self.saved = []

    def upsert_latest_prices(self, prices):
        self.saved.extend(prices)


def test_live_refresh_uses_bulk_and_falls_back_only_for_missing():
    lookup, repo = _Lookup(), _LatestRepo()
    service = LivePriceRefreshService(_Repo(), lookup, _Health(), latest_price_repo=repo)

    result = service.refresh_active_prices()

    assert lookup.single == ["CCC.IS"]  # yalnızca toplu istekte gelmeyen
    assert result.prices == {1: Decimal("10"), 2: Decimal("20"), 3: Decimal("30")}
    assert {p.stock_id: p.as_of.minute for p in repo.saved} == {1: 59, 2: 59, 3: 0}  # bar zamanı korunur
