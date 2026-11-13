"""FxRateService ve AssetPriceRefreshService (bellek içi sahte sağlayıcı ve repo'larla)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

import pytest

from src.application.services.assets.asset_price_refresh_service import AssetPriceRefreshService
from src.application.services.assets.fx_rate_service import FxRateService, fx_symbol
from src.domain.exceptions import MarketDataUnavailableError
from src.domain.models.asset import Asset, AssetClass
from src.domain.models.asset_price import AssetLatestPrice, AssetPrice, AssetQuote, FxRate
from src.domain.ports.repositories.i_asset_price_repo import IAssetPriceRepository
from src.domain.ports.repositories.i_asset_repo import IAssetRepository
from src.domain.ports.repositories.i_fx_rate_repo import IFxRateRepository
from src.domain.ports.services.i_asset_price_provider import IAssetPriceProvider

D = Decimal
NOW = datetime(2026, 1, 5, 15, 0)        # pazartesi 10:00 ET: ABD hisse ve metal açık
WEEKEND = datetime(2026, 1, 10, 15, 0)   # cumartesi: yalnızca kripto açık


class FakeProvider(IAssetPriceProvider):
    def __init__(self):
        self.quotes: Dict[str, AssetQuote] = {}
        self.history: Dict[str, List] = {}
        self.latest_calls: List[List[str]] = []
        self.fail_history = False

    def get_latest(self, symbols):
        self.latest_calls.append(list(symbols))
        return {s: self.quotes[s] for s in symbols if s in self.quotes}

    def get_history(self, symbol, start, end):
        if self.fail_history:
            raise MarketDataUnavailableError("ağ yok")
        return [p for p in self.history.get(symbol, []) if start <= p[0] <= end]


class FakeFxRepo(IFxRateRepository):
    def __init__(self):
        self.rates: Dict[tuple, FxRate] = {}

    def upsert_rates(self, rates):
        for rate in rates:
            self.rates[(rate.base_currency, rate.quote_currency, rate.rate_date)] = rate

    def get_rates(self, base_currency, quote_currency, start=None, end=None):
        return sorted(
            (r for (b, q, _), r in self.rates.items() if (b, q) == (base_currency, quote_currency)),
            key=lambda r: r.rate_date,
        )

    def get_rate_on_or_before(self, base_currency, quote_currency, on_date):
        candidates = [r for r in self.get_rates(base_currency, quote_currency) if r.rate_date <= on_date]
        return candidates[-1] if candidates else None


class FakeAssetRepo(IAssetRepository):
    def delete_all_assets(self):
        self.assets.clear()

    def __init__(self, assets: List[Asset]):
        self.assets = {a.id: a for a in assets}

    def add_asset(self, asset):  # pragma: no cover - kullanılmıyor
        raise NotImplementedError

    def get_asset(self, asset_id):
        return self.assets.get(asset_id)

    def get_asset_by_symbol(self, asset_class, symbol):  # pragma: no cover
        raise NotImplementedError

    def list_assets(self, active_only=True):
        return [a for a in self.assets.values() if a.is_active or not active_only]

    def set_active(self, asset_id, is_active):  # pragma: no cover
        self.assets[asset_id] = replace(self.assets[asset_id], is_active=is_active)

    def delete_asset(self, asset_id):  # pragma: no cover
        raise NotImplementedError


class FakePriceRepo(IAssetPriceRepository):
    def __init__(self):
        self.daily: List[AssetPrice] = []
        self.latest: Dict[int, AssetLatestPrice] = {}

    def upsert_daily_prices(self, prices):
        self.daily.extend(prices)

    def get_daily_prices(self, asset_id, start=None, end=None):  # pragma: no cover
        return [p for p in self.daily if p.asset_id == asset_id]

    def get_last_daily_price(self, asset_id, on_or_before=None):  # pragma: no cover
        raise NotImplementedError

    def upsert_latest_prices(self, prices):
        for price in prices:
            self.latest[price.asset_id] = price

    def get_latest_prices(self, asset_ids):  # pragma: no cover
        return {i: self.latest[i] for i in asset_ids if i in self.latest}

    def get_latest_price_map(self, asset_ids):  # pragma: no cover
        return {i: self.latest[i].price for i in asset_ids if i in self.latest}


def quote(symbol, price, as_of=NOW):
    return AssetQuote(symbol, D(price), as_of)


# ---------------- FxRateService ---------------- #


class TestFxRateService:
    @pytest.fixture
    def parts(self):
        provider, repo = FakeProvider(), FakeFxRepo()
        return provider, repo, FxRateService(provider, repo)

    def test_symbol_convention(self):
        assert fx_symbol("USD", "TRY") == "TRY=X"
        assert fx_symbol("eur", "try") == "EURTRY=X"

    def test_same_currency_rate_is_one(self, parts):
        assert parts[2].get_rate("try", "TRY") == D("1")

    def test_refresh_latest_stores_rates_by_provider_symbol(self, parts):
        provider, repo, service = parts
        provider.quotes = {"TRY=X": quote("TRY=X", "34.2", datetime(2026, 1, 5, 12, 0)), "EURTRY=X": quote("EURTRY=X", "37.5")}

        rates = service.refresh_latest(["USD", "eur", "TRY", "usd"])

        assert rates == {"USD": D("34.2"), "EUR": D("37.5")}
        assert provider.latest_calls == [["EURTRY=X", "TRY=X"]]
        assert repo.get_rate_on_or_before("USD", "TRY", date(2026, 1, 5)).rate == D("34.2")

    def test_refresh_skips_currencies_without_quote(self, parts):
        provider, repo, service = parts
        provider.quotes = {"TRY=X": quote("TRY=X", "34.2")}

        assert service.refresh_latest(["USD", "GBP"]) == {"USD": D("34.2")}
        assert repo.get_rates("GBP", "TRY") == []

    def test_get_rate_uses_latest_or_given_date(self, parts):
        _, repo, service = parts
        repo.upsert_rates([
            FxRate(None, "USD", "TRY", date(2026, 1, 1), D("34.0"), "yfinance"),
            FxRate(None, "USD", "TRY", date(2026, 1, 3), D("35.0"), "yfinance"),
        ])

        assert service.get_rate("USD", "TRY") == D("35.0")
        assert service.get_rate("USD", "TRY", date(2026, 1, 2)) == D("34.0")
        assert service.get_rate("USD", "TRY", date(2025, 12, 1)) is None

    def test_get_rate_dated_returns_rate_date_for_staleness(self, parts):
        _, repo, service = parts
        assert service.get_rate_dated("USD", "TRY") is None
        repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 3), D("35.0"), "yfinance")])

        assert service.get_rate_dated("USD", "TRY") == (D("35.0"), date(2026, 1, 3))
        assert service.get_rate_dated("TRY", "USD") == (D("1") / D("35.0"), date(2026, 1, 3))

    def test_inverse_rate_is_derived(self, parts):
        _, repo, service = parts
        repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 1), D("40"), "yfinance")])

        assert service.get_rate("TRY", "USD") == D("0.025")

    def test_convert(self, parts):
        _, repo, service = parts
        repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 1), D("34"), "yfinance")])

        assert service.convert(D("10"), "USD", "TRY") == D("340")
        assert service.convert(D("10"), "EUR", "TRY") is None

    def test_backfill_saves_history_in_range(self, parts):
        provider, repo, service = parts
        provider.history["TRY=X"] = [(date(2026, 1, d), D(str(30 + d))) for d in (1, 2, 3)]

        saved = service.backfill("USD", "TRY", start=date(2026, 1, 2), end=date(2026, 1, 3))

        assert saved == 2
        assert [r.rate for r in repo.get_rates("USD", "TRY")] == [D("32"), D("33")]


# ---------------- AssetPriceRefreshService ---------------- #


def make_assets():
    return [
        Asset(1, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD"),
        Asset(2, "AAPL", "Apple", AssetClass.US_STOCK, "USD", "AAPL"),
        Asset(3, "XAU", "Altın", AssetClass.PRECIOUS_METAL, "USD", "GC=F"),
        Asset(4, "OLD", "Pasif", AssetClass.CRYPTO, "USD", "OLD-USD", is_active=False),
    ]


@pytest.fixture
def refresh_parts():
    provider, price_repo = FakeProvider(), FakePriceRepo()
    state = {"now": NOW}
    service = AssetPriceRefreshService(
        FakeAssetRepo(make_assets()), price_repo, provider, now_provider=lambda: state["now"]
    )
    return provider, price_repo, service, state


class TestAssetPriceRefreshService:
    def test_refresh_stores_latest_prices_with_asset_currency(self, refresh_parts):
        provider, price_repo, service, _ = refresh_parts
        provider.quotes = {s: quote(s, p) for s, p in {"BTC-USD": "65000", "AAPL": "190.5", "GC=F": "2650"}.items()}

        result = service.refresh_latest()

        assert result.updated == ["BTC", "AAPL", "XAU"]
        assert result.missing == [] and result.skipped_closed == []
        assert price_repo.latest[2].price == D("190.5")
        assert price_repo.latest[2].currency_code == "USD"
        assert price_repo.latest[2].fetched_at == NOW
        assert 4 not in price_repo.latest
        assert provider.latest_calls == [["BTC-USD", "AAPL", "GC=F"]]

    def test_closed_markets_are_skipped_when_only_open(self, refresh_parts):
        provider, price_repo, service, state = refresh_parts
        state["now"] = WEEKEND
        provider.quotes = {"BTC-USD": quote("BTC-USD", "65000", WEEKEND)}

        result = service.refresh_latest(only_open=True)

        assert result.updated == ["BTC"]
        assert result.skipped_closed == ["AAPL", "XAU"]
        assert provider.latest_calls == [["BTC-USD"]]

    def test_only_open_false_refreshes_everything(self, refresh_parts):
        provider, _, service, state = refresh_parts
        state["now"] = WEEKEND
        provider.quotes = {"AAPL": quote("AAPL", "190", WEEKEND)}

        result = service.refresh_latest(only_open=False)

        assert result.updated == ["AAPL"]
        assert result.missing == ["BTC", "XAU"]

    def test_nothing_due_makes_no_provider_call(self, refresh_parts):
        provider, _, service, state = refresh_parts
        service._asset_repo = FakeAssetRepo([make_assets()[1]])  # yalnızca ABD hissesi
        state["now"] = WEEKEND

        result = service.refresh_latest()

        assert result.skipped_closed == ["AAPL"] and result.updated == []
        assert provider.latest_calls == []

    def test_backfill_history_saves_daily_closes(self, refresh_parts):
        provider, price_repo, service, _ = refresh_parts
        provider.history["GC=F"] = [(date(2026, 1, d), D(str(2600 + d))) for d in (1, 2, 5)]

        saved = service.backfill_history(3, start=date(2026, 1, 1), end=date(2026, 1, 5))

        assert saved == 3
        assert [(p.price_date.day, p.close_price, p.currency_code, p.asset_id) for p in price_repo.daily] == [
            (1, D("2601"), "USD", 3), (2, D("2602"), "USD", 3), (5, D("2605"), "USD", 3),
        ]

    def test_backfill_unknown_asset_raises(self, refresh_parts):
        with pytest.raises(ValueError, match="bulunamadı"):
            refresh_parts[2].backfill_history(99)

    def test_backfill_propagates_provider_outage(self, refresh_parts):
        provider, _, service, _ = refresh_parts
        provider.fail_history = True

        with pytest.raises(MarketDataUnavailableError):
            service.backfill_history(1)
