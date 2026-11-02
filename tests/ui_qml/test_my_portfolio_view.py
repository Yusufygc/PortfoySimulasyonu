"""Portföyüm sayfası uçtan uca: taze geçici veritabanında gerçek container, gerçek QML, sahte ağ yok.

Varlık ve fiyat kayıtları servis/repository üzerinden yazılır (sembol doğrulaması ve fiyat çekimi çağrılmaz); QML modalları,
sınıf sekmeleri ve USD anahtarı uyarısız çalışmalı, işlem kaydı özeti yeniden okutmalıdır.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, Q_ARG, QUrl, Qt
from PySide6.QtQml import QQmlComponent, QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtWidgets import QApplication

from src.application.container import AppContainer
from src.domain.models.asset import Asset, AssetClass
from src.domain.models.asset_price import AssetLatestPrice, FxRate
from src.domain.models.trade import TradeSide
from src.ui_qml.controllers.assets_controller import AssetsController
from src.ui_qml.controllers.cash_pool_controller import CashPoolController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.my_portfolio_controller import MyPortfolioController
from src.ui_qml.controllers.price_refresh_controller import PriceRefreshController
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.stock_detail_controller import StockDetailController
from src.ui_qml.controllers.system_controller import SystemController

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"
D = Decimal


@pytest.fixture(scope="module")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def pump(times: int = 8) -> None:
    for _ in range(times):
        QCoreApplication.processEvents()


def find(item, class_fragment):
    matches = [o for o in item.findChildren(QObject) if class_fragment in o.metaObject().className()]
    assert matches, f"{class_fragment} bulunamadı"
    return matches[0]


def invoke(obj, method, *args):
    QMetaObject.invokeMethod(obj, method, Qt.DirectConnection, *[Q_ARG("QVariant", a) for a in args])


@pytest.fixture
def env(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("DB_SQLITE_PATH", str(tmp_path / "fresh.db"))
    container = AppContainer()
    engine = QQmlApplicationEngine()
    system = SystemController(container=container, parent=engine)
    sync = MarketSyncController(parent=engine, container=container)
    controllers = {
        "shellController": ShellController(container=container, parent=engine),
        "chartController": ChartController(container=container, parent=engine),
        "dashboardController": DashboardController(container=container, parent=engine),
        "myPortfolioController": MyPortfolioController(container=container, parent=engine),
        "assetsController": AssetsController(container=container, parent=engine),
        "cashPoolController": CashPoolController(container=container, parent=engine),
        "stockDetailController": StockDetailController(container=container, parent=engine),
        "systemController": system,
        "marketSyncController": sync,
        "priceRefreshController": PriceRefreshController(system, sync, container=container, parent=engine),
    }
    controllers["assetsController"]._executor = type("Sync", (), {"submit": staticmethod(lambda fn: fn())})()
    controllers["assetsController"].dataChanged.connect(controllers["myPortfolioController"].reload)
    for name, controller in controllers.items():
        engine.rootContext().setContextProperty(name, controller)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    yield container, engine, controllers, warnings
    engine.deleteLater()


def load_view(engine):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "views" / "MyPortfolioView.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    assert item is not None
    item._component = component   # bileşen yok olursa oluşturulan öğe de silinir
    item.setProperty("width", 1280)
    item.setProperty("height", 820)
    pump()
    return item


def seed_btc(container):
    """0,5 BTC: 60.000 USD'den, kur 30 ile alındı; güncel fiyat 70.000 USD, güncel kur 40."""
    asset = container.asset_repo.add_asset(Asset(None, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD"))
    # ortak nakit havuzu: 900.000 TL yatır, 30.000 USD'yi kur 30'dan al, sonra BTC'yi USD nakitten öde
    container.cash_movement_service.add_deposit(D("900000"), movement_date=date(2026, 1, 1))
    container.fx_conversion_service.buy_usd(30000, rate=30, conversion_date=date(2026, 1, 2))
    container.asset_ledger_service.record_trade(
        asset.id, TradeSide.BUY, "0.5", "60000", trade_date=date(2026, 1, 2), fx_rate_to_try="30")
    now = datetime(2026, 1, 5, 12, 0)
    container.asset_price_repo.upsert_latest_prices([AssetLatestPrice(None, asset.id, D("70000"), "USD", now, "yfinance", now)])
    container.fx_rate_repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 5), D("40"), "yfinance")])
    return asset


class TestMyPortfolioPage:
    def test_empty_database_renders_without_warnings(self, env):
        _, engine, controllers, warnings = env
        item = load_view(engine)

        controllers["myPortfolioController"].setActiveClass("CRYPTO")
        pump()

        assert controllers["myPortfolioController"].holdingsCount == 0
        assert warnings == [], "\n".join(warnings)
        item.deleteLater()

    def test_asset_values_flow_from_database_to_page(self, env):
        container, engine, controllers, warnings = env
        seed_btc(container)
        item = load_view(engine)
        page = controllers["myPortfolioController"]

        page.reload()
        pump()

        assert page.totalValue == "₺1.400.000,00"           # 0,5 x 70.000 x 40
        assert page.unrealizedPL == "₺500.000,00"          # maliyet 0,5 x 60.000 x 30 = 900.000
        assert [s["classKey"] for s in page.allocationSlices] == ["CRYPTO"]
        assert page.tabCounts["CRYPTO"] == 1 and page.holdingsModel.rowCount() == 1

        page.setDisplayCurrency("USD")
        pump()
        assert page.totalValue == "$35.000,00"
        page.setActiveClass("BIST_STOCK")
        pump()
        assert page.holdingsModel.rowCount() == 0
        assert warnings == [], "\n".join(warnings)
        item.deleteLater()

    def test_modals_open_and_prefill_suggestion(self, env):
        container, engine, controllers, warnings = env
        asset = seed_btc(container)
        item = load_view(engine)

        add_modal, trade_modal = find(item, "AssetAddModal"), find(item, "AssetTradeModal")
        invoke(add_modal, "open")
        pump()
        assert add_modal.property("isOpen") is True
        invoke(add_modal, "close")

        invoke(trade_modal, "open", asset.id)
        pump()
        assert trade_modal.property("isOpen") is True
        assert trade_modal.property("currency") == "USD" and trade_modal.property("isTry") is False
        assert trade_modal.property("currentAssetId") == asset.id
        assert warnings == [], "\n".join(warnings)
        item.deleteLater()

    def test_recording_a_sell_updates_the_page(self, env):
        container, engine, controllers, warnings = env
        asset = seed_btc(container)
        item = load_view(engine)
        page, assets = controllers["myPortfolioController"], controllers["assetsController"]
        page.reload()
        results = []
        assets.tradeRecorded.connect(lambda ok, msg: results.append((ok, msg)))

        assets.recordTrade(asset.id, {"side": "SELL", "quantity": "0,25", "price": "72000", "date": "06.01.2026", "time": "10:00", "fx": "41"})
        pump()

        assert results == [(True, "BTC SATIM işlemi kaydedildi.")]
        # kalan 0,25 x 70.000 x 40 = 700.000 TL + satıştan gelen 0,25 x 72.000 = 18.000 USD nakit x 40 = 720.000 TL
        assert page.totalValue == "₺1.420.000,00"
        assert page.hasUsdCash and page.usdCashBalance == "$18.000,00"
        # Nakit kartı havuzun tamamıdır (TL + USD karşılığı); dağılımdaki Nakit dilimiyle aynı tutar
        assert page.cashBalance == "₺720.000,00" and page.cashBreakdown == "TL ₺0,00 + USD $18.000,00"
        assert next(s for s in page.allocationSlices if s["classKey"] == "CASH")["amount"] == page.cashBalance
        assert warnings == [], "\n".join(warnings)
        item.deleteLater()

    def test_oversell_is_rejected_and_page_unchanged(self, env):
        container, engine, controllers, warnings = env
        asset = seed_btc(container)
        page, assets = controllers["myPortfolioController"], controllers["assetsController"]
        page.reload()
        results = []
        assets.tradeRecorded.connect(lambda ok, msg: results.append((ok, msg)))

        assets.recordTrade(asset.id, {"side": "SELL", "quantity": "2", "price": "72000", "date": "06.01.2026", "time": "10:00", "fx": "41"})

        assert results[0][0] is False and "yeterli miktar" in results[0][1]
        assert page.totalValue == "₺1.400.000,00"

    def test_removing_asset_with_history_keeps_ledger_but_hides_asset(self, env):
        container, _, controllers, _ = env
        asset = seed_btc(container)
        assets = controllers["assetsController"]

        assets.removeAsset(asset.id)

        assert assets.assets == []
        assert len(container.asset_ledger_service.get_trades(asset.id)) == 1
