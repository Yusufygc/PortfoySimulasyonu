"""WatchlistController — WatchlistView'un d3 veri köprüsü testleri."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.analysis.stock_360_service import StockOverview
from src.domain.models.stock import Stock
from src.domain.models.watchlist import Watchlist
from src.ui_qml.controllers.watchlist_controller import WatchlistController


def _watchlist(id_: int, name: str) -> Watchlist:
    return Watchlist(id=id_, name=name)


def _overview(ticker: str, price: str, change: float) -> StockOverview:
    return StockOverview(
        ticker=ticker, last_price=Decimal(price), last_price_date=date.today(),
        daily_change_pct=change, volume=1000, week52_low=Decimal("1"), week52_high=Decimal("999"),
    )


def _make_container(watchlists=None, watchlist_stocks=None, overview_map=None):
    container = MagicMock()
    container.watchlist_service.get_all_watchlists.return_value = watchlists or []
    container.watchlist_service.get_watchlist_stocks.return_value = watchlist_stocks or []

    overview_map = overview_map or {}
    container.stock_360_service.get_overview.side_effect = lambda t: overview_map.get(t)
    return container


class TestWatchlistSelection:
    def test_refresh_populates_watchlist_lists(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "Favoriler"), _watchlist(2, "İzleme")])
        controller = WatchlistController(container)

        assert controller.watchlistIds == [1, 2]
        assert controller.watchlistNames == ["Favoriler", "İzleme"]

    def test_first_watchlist_becomes_active_by_default(self, qapp):
        container = _make_container(watchlists=[_watchlist(5, "Favoriler")])
        controller = WatchlistController(container)
        assert controller.activeWatchlistId == 5

    def test_no_watchlists_gives_inactive_state(self, qapp):
        controller = WatchlistController(_make_container(watchlists=[]))
        assert controller.activeWatchlistId == -1
        assert controller.itemTickers == []

    def test_select_watchlist_switches_active_and_reloads_items(self, qapp):
        stocks_by_list = {
            1: [{"item": None, "stock": None, "ticker": "AKBNK", "name": "Akbank"}],
            2: [{"item": None, "stock": None, "ticker": "THYAO", "name": "THY"}],
        }
        container = _make_container(watchlists=[_watchlist(1, "A"), _watchlist(2, "B")])
        container.watchlist_service.get_watchlist_stocks.side_effect = lambda wid: stocks_by_list[wid]
        controller = WatchlistController(container)
        assert controller.itemTickers == ["AKBNK"]

        controller.selectWatchlist(2)

        assert controller.activeWatchlistId == 2
        assert controller.itemTickers == ["THYAO"]

    def test_select_unknown_watchlist_id_is_ignored(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "A")])
        controller = WatchlistController(container)
        controller.selectWatchlist(999)
        assert controller.activeWatchlistId == 1


class TestItemsWithPrices:
    def test_items_include_price_and_daily_change_from_overview(self, qapp):
        container = _make_container(
            watchlists=[_watchlist(1, "A")],
            watchlist_stocks=[{"item": None, "stock": None, "ticker": "AKBNK", "name": "Akbank"}],
            overview_map={"AKBNK": _overview("AKBNK", "120", 1.5)},
        )
        controller = WatchlistController(container)

        assert controller.itemNames == ["Akbank"]
        assert controller.itemPrices == [120.0]
        assert controller.itemDailyChangePct == [1.5]

    def test_missing_overview_gives_zero_price(self, qapp):
        container = _make_container(
            watchlists=[_watchlist(1, "A")],
            watchlist_stocks=[{"item": None, "stock": None, "ticker": "YOK", "name": "Yok Hisse"}],
        )
        controller = WatchlistController(container)
        assert controller.itemPrices == [0.0]


class TestCreateWatchlist:
    def test_create_watchlist_adds_and_selects_it(self, qapp):
        container = _make_container(watchlists=[])
        created = _watchlist(7, "Yeni Liste")
        container.watchlist_service.create_watchlist.return_value = created

        def refreshed_watchlists():
            return [created]
        container.watchlist_service.get_all_watchlists.side_effect = None
        container.watchlist_service.get_all_watchlists.return_value = [created]

        controller = WatchlistController(container)
        controller.createWatchlist("Yeni Liste")

        assert controller.activeWatchlistId == 7
        assert controller.error == ""

    def test_create_watchlist_failure_sets_error(self, qapp):
        container = _make_container(watchlists=[])
        container.watchlist_service.create_watchlist.side_effect = ValueError("Bu isimde bir liste zaten var.")

        controller = WatchlistController(container)
        controller.createWatchlist("Var Olan")

        assert "zaten var" in controller.error


class TestAddRemoveTicker:
    def test_add_ticker_delegates_and_refreshes(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "A")])
        controller = WatchlistController(container)

        controller.addTicker("thyao")

        container.watchlist_service.add_stock_by_ticker.assert_called_once_with(1, "thyao")
        assert controller.error == ""

    def test_add_ticker_without_active_watchlist_sets_error(self, qapp):
        controller = WatchlistController(_make_container(watchlists=[]))
        controller.addTicker("THYAO")
        assert controller.error != ""

    def test_add_ticker_failure_sets_error(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "A")])
        container.watchlist_service.add_stock_by_ticker.side_effect = ValueError("Bu hisse zaten listede mevcut: THYAO")

        controller = WatchlistController(container)
        controller.addTicker("THYAO")

        assert "zaten listede" in controller.error

    def test_remove_ticker_delegates_with_resolved_stock_id(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "A")])
        container.stock_repo.get_stock_by_ticker.return_value = Stock(id=42, ticker="THYAO", name="THY", currency_code="TRY")

        controller = WatchlistController(container)
        controller.removeTicker("thyao")

        container.watchlist_service.remove_stock_from_watchlist.assert_called_once_with(1, 42)

    def test_remove_unknown_ticker_is_noop(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "A")])
        container.stock_repo.get_stock_by_ticker.return_value = None

        controller = WatchlistController(container)
        controller.removeTicker("YOK")

        container.watchlist_service.remove_stock_from_watchlist.assert_not_called()


class TestDeleteWatchlist:
    def test_delete_active_watchlist_delegates_and_clears_active(self, qapp):
        container = _make_container(watchlists=[_watchlist(1, "A")])
        controller = WatchlistController(container)

        container.watchlist_service.get_all_watchlists.return_value = []
        controller.deleteActiveWatchlist()

        container.watchlist_service.delete_watchlist.assert_called_once_with(1)
        assert controller.activeWatchlistId == -1
