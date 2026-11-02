"""AssetsController: varlık ekleme (arka plan), işlem kaydı doğrulaması, fiyat yenileme ve öneri (sahte servislerle)."""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication

from src.application.services.assets.asset_catalog import ASSET_CATALOG
from src.application.services.assets.asset_price_refresh_service import AssetRefreshResult
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.trade import TradeSide
from src.ui_qml.controllers.assets_controller import AssetsController, parse_date_text, parse_time_text

D = Decimal


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


class SyncExecutor:
    """Arka plan işini aynı iş parçacığında çalıştırır (testler gerçek iş parçacığı beklemez)."""

    def submit(self, fn):
        fn()


class FakeLedger:
    catalog = ASSET_CATALOG

    def __init__(self):
        self.assets = [
            Asset(1, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD"),
            Asset(2, "GAU", "Gram altın", AssetClass.PRECIOUS_METAL, "TRY", "GAU", AssetUnit.GRAM),
        ]
        self.add_error = None
        self.trade_error = None
        self.trades = []
        self.removed = []

    def list_assets(self, active_only=True):
        return list(self.assets)

    def get_asset(self, asset_id):
        return next((a for a in self.assets if a.id == asset_id), None)

    def add_catalog_asset(self, key):
        if self.add_error:
            raise ValueError(self.add_error)
        return Asset(9, key, "Katalog", AssetClass.CRYPTO, "USD", f"{key}-USD")

    def add_asset(self, symbol, name, asset_class, currency, **options):
        if self.add_error:
            raise ValueError(self.add_error)
        return Asset(10, symbol.upper(), name, asset_class, currency, symbol.upper())

    def record_trade(self, asset_id, side, quantity, price, **options):
        if self.trade_error:
            raise ValueError(self.trade_error)
        self.trades.append(
            (asset_id, side, quantity, price, options["trade_date"], options.get("trade_time"), options.get("fx_rate_to_try"))
        )
        return SimpleNamespace(side=side)

    def remove_asset(self, asset_id):
        if asset_id == 99:
            raise ValueError("Varlık bulunamadı.")
        self.removed.append(asset_id)


class FakeRefresh:
    def __init__(self):
        self.backfilled, self.refresh_calls = [], []
        self.fail_history = False

    def backfill_history(self, asset_id):
        if self.fail_history:
            raise RuntimeError("ağ yok")
        self.backfilled.append(asset_id)

    def refresh_latest(self, only_open=True):
        self.refresh_calls.append(only_open)
        return AssetRefreshResult(updated=["BTC", "GAU"])

    def cached_price(self, asset_id):
        return {1: D("65000"), 2: D("3110.34768")}.get(asset_id)


class FakeFx:
    def __init__(self, rate="40"):
        self.rate = None if rate is None else D(rate)
        self.refreshed, self.backfilled = [], []

    def get_rate(self, base, quote, on_date=None):
        return self.rate

    def refresh_latest(self, currencies, quote_currency="TRY"):
        self.refreshed.append(sorted(currencies))
        return {}

    def backfill(self, base, quote="TRY", start=None, end=None):
        self.backfilled.append(base)
        self.rate = D("40")
        return 1


@pytest.fixture
def parts(qapp):
    ledger, refresh, fx = FakeLedger(), FakeRefresh(), FakeFx()
    container = SimpleNamespace(asset_ledger_service=ledger, asset_price_refresh_service=refresh, fx_rate_service=fx)
    controller = AssetsController(container=container)
    controller._executor = SyncExecutor()
    return ledger, refresh, fx, controller


def capture(controller):
    log = {"added": [], "trade": [], "removed": [], "prices": [], "data": 0, "assets": 0}
    controller.assetAdded.connect(lambda ok, msg: log["added"].append((ok, msg)))
    controller.tradeRecorded.connect(lambda ok, msg: log["trade"].append((ok, msg)))
    controller.assetRemoved.connect(lambda ok, msg: log["removed"].append((ok, msg)))
    controller.pricesRefreshed.connect(lambda ok, msg: log["prices"].append((ok, msg)))
    controller.dataChanged.connect(lambda: log.__setitem__("data", log["data"] + 1))
    controller.assetsChanged.connect(lambda: log.__setitem__("assets", log["assets"] + 1))
    return log


class TestParsing:
    @pytest.mark.parametrize(
        "text,expected", [("05.01.2026", date(2026, 1, 5)), ("2026-01-05", date(2026, 1, 5)), ("5/1/26", None)]
    )
    def test_parse_date(self, text, expected):
        assert parse_date_text(text) == expected

    @pytest.mark.parametrize("text,expected", [("10:30", time(10, 30)), ("10:30:15", time(10, 30, 15)), ("25:99", None)])
    def test_parse_time(self, text, expected):
        assert parse_time_text(text) == expected

    def test_blank_date_and_time_default_to_now(self):
        assert isinstance(parse_date_text(""), date) and isinstance(parse_time_text(" "), time)


class TestLists:
    def test_catalog_and_assets_are_plain_dicts(self, parts):
        controller = parts[3]

        assert {"key": "XAU", "name": "Altın (gram)", "classKey": "PRECIOUS_METAL", "currency": "TRY"} in controller.catalog
        assert controller.assets[0] == {
            "id": 1, "symbol": "BTC", "name": "Bitcoin", "classKey": "CRYPTO", "currency": "USD", "isTry": False, "unit": "UNIT",
        }
        assert controller.assets[1]["isTry"] is True and controller.assets[1]["unit"] == "GRAM"

    def test_without_container_everything_is_empty(self, qapp):
        controller = AssetsController(container=None)

        assert controller.catalog == [] and controller.assets == [] and controller.suggest(1) == {}


class TestAddAsset:
    def test_catalog_add_loads_history_price_and_fx_then_signals(self, parts):
        _, refresh, fx, controller = parts
        log = capture(controller)

        controller.addCatalogAsset("BTC")

        assert log["added"] == [(True, "BTC eklendi.")]
        assert refresh.backfilled == [9] and refresh.refresh_calls == [False]
        assert fx.refreshed == [["USD"]]
        assert log["data"] == 1 and log["assets"] == 1 and not controller.busy

    def test_missing_fx_history_is_backfilled_first(self, parts):
        _, _, fx, controller = parts
        fx.rate = None

        controller.addCatalogAsset("BTC")

        assert fx.backfilled == ["USD"]

    def test_partial_load_failure_is_reported_but_asset_is_added(self, parts):
        _, refresh, _, controller = parts
        refresh.fail_history = True
        log = capture(controller)

        controller.addCatalogAsset("BTC")

        assert log["added"] == [(True, "BTC eklendi. (geçmiş yüklenemedi; daha sonra yenilenecek)")]

    def test_validation_error_is_reported_without_data_change(self, parts):
        ledger, _, _, controller = parts
        ledger.add_error = "ZZZZ sembolü için fiyat verisi bulunamadı."
        log = capture(controller)

        controller.addAsset("zzzz", "", "US_STOCK", "USD")

        assert log["added"] == [(False, "ZZZZ sembolü için fiyat verisi bulunamadı.")]
        assert log["data"] == 0 and not controller.busy

    def test_add_by_symbol_defaults_name_to_symbol(self, parts):
        controller = parts[3]
        log = capture(controller)

        controller.addAsset("aapl", "  ", "US_STOCK", "USD")

        assert log["added"] == [(True, "AAPL eklendi.")]

    def test_unknown_class_is_rejected(self, parts):
        controller = parts[3]
        log = capture(controller)

        controller.addAsset("AAPL", "Apple", "ETF", "USD")

        assert log["added"] == [(False, "Varlık sınıfı geçersiz.")]

    def test_second_job_is_rejected_while_busy(self, parts):
        controller = parts[3]
        controller._busy = True
        log = capture(controller)

        controller.addCatalogAsset("BTC")

        assert log["added"] == [(False, "Başka bir işlem sürüyor, bitmesini bekleyin.")]
        assert controller.busy


class TestRefreshPrices:
    def test_refreshes_fx_for_foreign_assets_and_prices(self, parts):
        _, refresh, fx, controller = parts
        log = capture(controller)

        controller.refreshPrices()

        assert fx.refreshed == [["USD"]] and refresh.refresh_calls == [False]
        assert log["prices"] == [(True, "2 varlık fiyatı güncellendi.")] and log["data"] == 1

    def test_only_open_flag_is_forwarded(self, parts):
        refresh, controller = parts[1], parts[3]

        controller.refreshPrices(True)

        assert refresh.refresh_calls == [True]

    def test_autostart_is_off_by_default(self, parts):
        assert not parts[3]._timer.isActive()


def form(*values):
    """İşlem penceresi alanları sırasıyla: yön, miktar, fiyat, tarih, saat, kur."""
    return dict(zip(("side", "quantity", "price", "date", "time", "fx"), values))


class TestRecordTrade:
    def test_records_trade_with_parsed_values(self, parts):
        ledger, _, _, controller = parts
        log = capture(controller)

        controller.recordTrade(1, form("buy", "0,5", "65.000", "05.01.2026", "10:30", "40,25"))

        assert ledger.trades == [(1, TradeSide.BUY, D("0.5"), D("65000"), date(2026, 1, 5), time(10, 30), D("40.25"))]
        assert log["trade"] == [(True, "BTC ALIM işlemi kaydedildi.")] and log["data"] == 1

    def test_sell_label_and_blank_fx(self, parts):
        ledger, _, _, controller = parts
        log = capture(controller)

        controller.recordTrade(2, form("SELL", "10", "2500", "05.01.2026", "10:30", ""))

        assert ledger.trades[0][6] is None
        assert log["trade"] == [(True, "GAU SATIM işlemi kaydedildi.")]

    @pytest.mark.parametrize(
        "args,message",
        [
            ((1, "HOLD", "1", "1", "", "", ""), "yönü"),
            ((1, "BUY", "0", "1", "", "", ""), "Miktar"),
            ((1, "BUY", "abc", "1", "", "", ""), "Miktar"),
            ((1, "BUY", "1", "-5", "", "", ""), "Fiyat"),
            ((1, "BUY", "1", "1", "31/12/2026", "", ""), "Tarih"),
            ((1, "BUY", "1", "1", "05.01.2026", "99:99", ""), "Saat"),
            ((1, "BUY", "1", "1", "05.01.2026", "10:30", "0"), "Kur"),
        ],
    )
    def test_invalid_input_never_reaches_the_service(self, parts, args, message):
        ledger, _, _, controller = parts
        log = capture(controller)

        controller.recordTrade(args[0], form(*args[1:]))

        assert ledger.trades == [] and log["data"] == 0
        assert log["trade"][0][0] is False and message in log["trade"][0][1]

    def test_service_rejection_is_forwarded(self, parts):
        ledger, _, _, controller = parts
        ledger.trade_error = "BTC: işlem sonrası elde yeterli miktar kalmıyor."
        log = capture(controller)

        controller.recordTrade(1, form("SELL", "5", "100", "05.01.2026", "10:30", "40"))

        assert log["trade"] == [(False, "BTC: işlem sonrası elde yeterli miktar kalmıyor.")] and log["data"] == 0


class TestSuggestAndRemove:
    def test_suggest_foreign_asset(self, parts):
        suggestion = parts[3].suggest(1)
        assert {k: v for k, v in suggestion.items() if k != "cash"} == {"currency": "USD", "isTry": False, "price": "65000", "fxRate": "40.0000"}

    def test_suggest_converts_ounce_quote_for_gram_asset(self, parts):
        suggestion = parts[3].suggest(2)

        assert suggestion["price"] == "100" and suggestion["isTry"] is True and suggestion["fxRate"] == ""

    def test_suggest_unknown_asset(self, parts):
        assert parts[3].suggest(404) == {}

    def test_remove_asset_signals_and_reports_errors(self, parts):
        ledger, _, _, controller = parts
        log = capture(controller)

        controller.removeAsset(1)
        controller.removeAsset(99)

        assert ledger.removed == [1]
        assert log["removed"] == [(True, "Varlık kaldırıldı."), (False, "Varlık bulunamadı.")]
        assert log["data"] == 1 and log["assets"] == 1
