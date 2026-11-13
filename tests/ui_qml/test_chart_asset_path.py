"""ChartController: BIST'te bulunamayan sembol varlık defterinden çizilir; BIST yolu önceliklidir."""
from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.assets.asset_chart_service import AssetChartService
from src.domain.market_clock import market_today
from src.domain.models.asset import Asset, AssetClass
from src.domain.models.asset_price import AssetPrice
from src.ui_qml.controllers.chart_controller import ChartController

BTC = Asset(1, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD")


class _Lookup:
    """BIST tarafı boş: hiçbir sembol bulunamaz."""

    def get_market_bars(self, ticker, start, end):
        return []

    def find_stock(self, ticker):
        return None

    def get_price_series(self, stock_id, start, end):
        return []


def _chart_service(with_prices=True) -> AssetChartService:
    today = market_today()
    rows = [AssetPrice(None, 1, today - timedelta(days=i), Decimal(60000 + i * 100), "USD", "t") for i in range(5)]
    ledger = SimpleNamespace(list_assets=lambda active_only=True: [BTC])
    return AssetChartService(ledger, SimpleNamespace(get_daily_prices=lambda *a, **k: rows if with_prices else []))


def _run(container, ticker):
    controller = ChartController(container=container)
    events = []
    controller.chartDataLoaded.connect(lambda t, payload: events.append(json.loads(payload)))
    controller.loadTicker(ticker)
    return controller, events[-1]


def test_asset_symbol_chart_uses_ledger_prices_and_currency_prefix():
    container = SimpleNamespace(stock_lookup_service=_Lookup(), asset_chart_service=_chart_service())
    controller, payload = _run(container, "btc-usd")
    assert payload["ticker"] == "BTC-USD" and payload["companyName"] == "Bitcoin"
    assert len(payload["candles"]) == 5
    assert controller.lastPrice.startswith("$") and controller.companyName == "Bitcoin"


def test_bist_ticker_without_data_still_returns_empty_chart_not_asset():
    container = SimpleNamespace(stock_lookup_service=_Lookup(), asset_chart_service=_chart_service())
    controller, payload = _run(container, "THYAO")
    assert payload["candles"] == [] and controller.lastPrice == "₺0,00"


def test_currency_resets_after_switching_back_from_asset():
    container = SimpleNamespace(stock_lookup_service=_Lookup(), asset_chart_service=_chart_service())
    controller, _ = _run(container, "BTC-USD")
    controller.loadTicker("THYAO")
    assert controller._price_currency == "TRY"


def test_asset_without_prices_falls_back_to_empty_chart():
    container = SimpleNamespace(stock_lookup_service=_Lookup(), asset_chart_service=_chart_service(with_prices=False))
    _, payload = _run(container, "BTC-USD")
    assert payload["candles"] == []


def test_quick_assets_for_selector_and_without_service():
    container = SimpleNamespace(stock_lookup_service=_Lookup(), asset_chart_service=_chart_service())
    assert ChartController(container=container).quickAssets == [{"ticker": "BTC-USD", "label": "BTC"}]
    assert ChartController(container=SimpleNamespace(stock_lookup_service=_Lookup())).quickAssets == []
    assert ChartController(container=None).quickAssets == []
