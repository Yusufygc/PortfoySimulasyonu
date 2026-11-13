"""AssetChartService ve grafiğin varlık yolu: sembol eşleme, kapanış serisi, mum üretimi."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.assets.asset_chart_service import AssetChartService
from src.domain.market_clock import market_today
from src.domain.models.asset import Asset, AssetClass
from src.domain.models.asset_price import AssetPrice
from src.ui_qml.controllers.chart_candle_sources import last_price_summary, load_asset_candles

BTC = Asset(1, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD")
GOLD = Asset(2, "XAU", "Altın (ons)", AssetClass.PRECIOUS_METAL, "USD", "GC=F")


def _service(prices: dict[int, list[tuple[date, str]]] | None = None, assets=(BTC, GOLD)):
    prices = prices or {}

    def daily(asset_id, start=None, end=None):
        return [AssetPrice(None, asset_id, d, Decimal(p), "USD", "t") for d, p in prices.get(asset_id, [])]

    ledger = SimpleNamespace(list_assets=lambda active_only=True: list(assets))
    return AssetChartService(ledger, SimpleNamespace(get_daily_prices=daily))


class TestAssetChartService:
    def test_find_by_symbol_or_yf_symbol_case_insensitive(self):
        service = _service()
        assert service.find_asset("btc") is BTC
        assert service.find_asset("BTC-USD") is BTC
        assert service.find_asset("gc=f") is GOLD
        assert service.find_asset("THYAO") is None
        assert service.find_asset("") is None

    def test_series_sorted_ascending_with_currency(self):
        today = market_today()
        rows = [(today, "101"), (today - timedelta(days=2), "99"), (today - timedelta(days=1), "100")]
        series = _service({1: rows}).get_series("BTC-USD")
        assert [p[1] for p in series.points] == [Decimal("99"), Decimal("100"), Decimal("101")]
        assert series.currency == "USD" and series.name == "Bitcoin"

    def test_unknown_symbol_returns_none(self):
        assert _service().get_series("THYAO") is None

    def test_chart_symbols_use_yf_symbol_and_short_label(self):
        assert _service().list_chart_symbols() == [("BTC-USD", "BTC"), ("GC=F", "XAU")]


class TestAssetCandles:
    def test_candles_built_from_close_series(self):
        today = market_today()
        service = _service({1: [(today - timedelta(days=1), "100"), (today, "110")]})
        candles, volumes, name, currency = load_asset_candles(service, "BTC-USD")
        assert [c["close"] for c in candles] == [100.0, 110.0]
        assert all(c["low"] <= c["open"] <= c["high"] and c["low"] <= c["close"] <= c["high"] for c in candles)
        assert len(volumes) == 2 and name == "Bitcoin" and currency == "USD"

    def test_low_priced_asset_keeps_precision(self):
        doge = Asset(3, "DOGE", "Dogecoin", AssetClass.CRYPTO, "USD", "DOGE-USD")
        service = _service({3: [(market_today(), "0.153421")]}, assets=(doge,))
        candles, *_ = load_asset_candles(service, "DOGE-USD")
        assert candles[0]["close"] == 0.153421

    def test_none_when_no_asset_no_prices_or_failure(self):
        assert load_asset_candles(_service(), "BTC-USD") is None  # varlık var, fiyat yok
        assert load_asset_candles(_service(), "THYAO") is None
        assert load_asset_candles(None, "BTC-USD") is None
        broken = SimpleNamespace(get_series=lambda ticker: (_ for _ in ()).throw(RuntimeError("db")))
        assert load_asset_candles(broken, "BTC-USD") is None


class TestLastPriceSummary:
    CANDLES = [{"open": 100.0, "close": 100.0}, {"open": 100.0, "close": 110.0}]

    def test_try_default_unchanged(self):
        assert last_price_summary(self.CANDLES) == ("₺110,00", True, "+%10,00")

    def test_usd_prefix_and_small_price_precision(self):
        assert last_price_summary(self.CANDLES, "USD")[0] == "$110,00"
        small = [{"open": 0.15, "close": 0.15}, {"open": 0.15, "close": 0.153421}]
        assert last_price_summary(small, "USD")[0] == "$0,153421"
        assert last_price_summary(small, "TRY")[0] == "₺0,15"  # BIST biçimi korunur
