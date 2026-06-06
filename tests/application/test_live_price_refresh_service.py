from datetime import datetime, timezone
from decimal import Decimal

from src.application.services.market.live_price_refresh_service import LivePriceRefreshService
from src.application.services.market.price_lookup_service import PriceLookupResult


class FakeStockRepo:
    def __init__(self):
        self.requests = []

    def get_ticker_map_for_stock_ids(self, stock_ids):
        self.requests.append(list(stock_ids))
        return {
            1: "AAA.IS",
            2: "BBB.IS",
            3: "CCC.IS",
            4: "DDD.IS",
        }


class FakePriceLookupService:
    def __init__(self, results):
        self._results = results
        self.requests = []

    def lookup_price_for_ticker(self, ticker):
        self.requests.append(ticker)
        result = self._results.get(ticker)
        if isinstance(result, Exception):
            raise result
        return result


class FakePriceDataHealthService:
    def __init__(self, active_ids_by_scope):
        self._active_ids_by_scope = active_ids_by_scope
        self.requests = []

    def active_stock_ids(self, scope=None):
        self.requests.append(scope)
        return set(self._active_ids_by_scope.get(scope, self._active_ids_by_scope.get("all_active", set())))


class FakeLatestPriceRepo:
    def __init__(self):
        self.saved = []

    def upsert_latest_prices(self, prices):
        self.saved.append(list(prices))


def _lookup_result(price):
    return PriceLookupResult(
        price=Decimal(price),
        as_of=datetime(2026, 6, 3, 9, 30, tzinfo=timezone.utc),
        source="intraday",
    )


def make_service(active_ids_by_scope, lookup_results):
    stock_repo = FakeStockRepo()
    lookup_service = FakePriceLookupService(lookup_results)
    health_service = FakePriceDataHealthService(active_ids_by_scope)
    latest_price_repo = FakeLatestPriceRepo()
    service = LivePriceRefreshService(
        stock_repo=stock_repo,
        price_lookup_service=lookup_service,
        price_data_health_service=health_service,
        latest_price_repo=latest_price_repo,
    )
    return service, stock_repo, lookup_service, health_service, latest_price_repo


def test_live_price_refresh_scans_all_active_open_positions_only():
    service, stock_repo, lookup_service, health_service, latest_price_repo = make_service(
        {"all_active": {1, 3}},
        {"AAA.IS": _lookup_result("10.50"), "CCC.IS": _lookup_result("30.25")},
    )

    result = service.refresh_active_prices()

    assert health_service.requests == ["all_active"]
    assert stock_repo.requests == [[1, 3]]
    assert lookup_service.requests == ["AAA.IS", "CCC.IS"]
    assert result.scanned_count == 2
    assert result.updated_count == 2
    assert result.prices == {1: Decimal("10.50"), 3: Decimal("30.25")}
    saved_prices = latest_price_repo.saved[0]
    assert [(item.stock_id, item.price, item.source, item.provider) for item in saved_prices] == [
        (1, Decimal("10.50"), "intraday", "price_lookup"),
        (3, Decimal("30.25"), "intraday", "price_lookup"),
    ]


def test_live_price_refresh_honors_selected_scope_from_shared_resolver():
    service, _, lookup_service, health_service, _ = make_service(
        {
            "all_active": {1, 2, 3},
            "dashboard": {1},
            "model:4": {2, 3},
        },
        {"BBB.IS": _lookup_result("20"), "CCC.IS": _lookup_result("30")},
    )

    result = service.refresh_active_prices(scope="model:4")

    assert health_service.requests == ["model:4"]
    assert lookup_service.requests == ["BBB.IS", "CCC.IS"]
    assert result.prices == {2: Decimal("20"), 3: Decimal("30")}


def test_live_price_refresh_continues_when_lookup_returns_empty_or_errors():
    service, _, lookup_service, _, latest_price_repo = make_service(
        {"all_active": {1, 2, 3}},
        {
            "AAA.IS": _lookup_result("10"),
            "BBB.IS": None,
            "CCC.IS": ValueError("provider failed"),
        },
    )

    result = service.refresh_active_prices()

    assert lookup_service.requests == ["AAA.IS", "BBB.IS", "CCC.IS"]
    assert result.scanned_count == 3
    assert result.updated_count == 1
    assert result.prices == {1: Decimal("10")}
    assert len(result.errors) == 2
    assert any("BBB.IS" in error for error in result.errors)
    assert any("CCC.IS" in error for error in result.errors)
    assert [item.stock_id for item in latest_price_repo.saved[0]] == [1]


def test_live_price_refresh_has_no_daily_price_repo_dependency():
    service = LivePriceRefreshService(
        stock_repo=FakeStockRepo(),
        price_lookup_service=FakePriceLookupService({"AAA.IS": _lookup_result("10")}),
        price_data_health_service=FakePriceDataHealthService({"all_active": {1}}),
    )

    result = service.refresh_active_prices()

    assert result.prices == {1: Decimal("10")}
    assert not hasattr(service, "_price_repo")
