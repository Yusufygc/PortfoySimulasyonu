"""Üst piyasa şeridi servisi ve denetleyicisi."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.market.market_indicators_service import MarketIndicatorsService
from src.domain.models.market_indicator import IndicatorQuote, MarketIndicator
from src.infrastructure.market_data.yfinance_indicator_provider import YFinanceIndicatorProvider
from src.ui_qml.controllers.market_ticker_controller import MarketTickerController, indicator_to_dict

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class FakeProvider:
    def __init__(self, quotes):
        self.quotes = quotes

    def get_quote(self, symbol):
        return self.quotes.get(symbol)


def test_indicators_are_ordered_and_metals_converted_to_try_per_gram():
    provider = FakeProvider({
        "TRY=X": IndicatorQuote(40.0, 39.0),
        "EURTRY=X": IndicatorQuote(44.0, 44.0),
        "XU100.IS": IndicatorQuote(10000.0, 9900.0),
        "GC=F": IndicatorQuote(3110.35, 3000.0),
        "SI=F": IndicatorQuote(31.1035, None),
    })

    result = MarketIndicatorsService(provider).get_indicators()

    assert [i.label for i in result] == ["ALTIN", "GÜMÜŞ", "USD/TRY", "EUR/TRY", "BIST 100"]
    gold = result[0]
    assert gold.value == pytest.approx(3110.35 * 40.0 / 31.1035) and gold.currency == "₺"
    assert gold.change_pct == pytest.approx((3110.35 - 3000.0) / 3000.0 * 100)
    assert result[1].change_pct is None
    assert result[2].change_pct == pytest.approx((40 - 39) / 39 * 100) and result[4].currency == ""


def test_missing_indicators_are_skipped_and_metals_fall_back_to_usd_without_fx():
    provider = FakeProvider({"GC=F": IndicatorQuote(3110.35), "XU100.IS": IndicatorQuote(10000.0)})

    result = MarketIndicatorsService(provider).get_indicators()

    assert [i.label for i in result] == ["ALTIN", "BIST 100"]
    assert result[0].value == pytest.approx(100.0) and result[0].currency == "$"
    assert MarketIndicatorsService(FakeProvider({})).get_indicators() == []


def test_indicator_dict_formats_turkish_numbers():
    item = indicator_to_dict(MarketIndicator("USD/TRY", 41.2345, "₺", -0.5))

    assert item["valueText"] == "41,23 ₺" and item["changeText"] == "-0,50%"
    assert item["hasChange"] is True and item["isUp"] is False
    assert indicator_to_dict(MarketIndicator("BIST 100", 10234.5, "", None))["valueText"] == "10.234,50"


def test_yfinance_provider_reads_fast_info_and_never_raises(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            self.fast_info = {"lastPrice": 12.5, "previousClose": 12.0} if symbol == "OK" else None

    import yfinance

    monkeypatch.setattr(yfinance, "Ticker", FakeTicker)
    provider = YFinanceIndicatorProvider()

    assert provider.get_quote("OK") == IndicatorQuote(12.5, 12.0)
    assert provider.get_quote("YOK") is None

    def boom(_symbol):
        raise RuntimeError("ağ")

    monkeypatch.setattr(yfinance, "Ticker", boom)
    assert provider.get_quote("OK") is None


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _controller(qapp, service):
    ctrl = MarketTickerController(container=SimpleNamespace(market_indicators_service=service), autostart=False)
    ctrl._executor = ImmediateExecutor()
    return ctrl


def test_controller_keeps_last_values_when_refresh_fails(qapp):
    calls = iter([[MarketIndicator("USD/TRY", 40.0, "₺", 1.0)], RuntimeError("ağ yok"), []])

    def get_indicators():
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    ctrl = _controller(qapp, SimpleNamespace(get_indicators=get_indicators))

    ctrl.refresh()
    assert [i["label"] for i in ctrl.items] == ["USD/TRY"]
    ctrl.refresh()  # hata
    ctrl.refresh()  # boş sonuç
    assert [i["label"] for i in ctrl.items] == ["USD/TRY"] and ctrl.isLoading is False


def test_controller_without_service_is_inert(qapp):
    ctrl = MarketTickerController(container=None, autostart=False)

    ctrl.refresh()

    assert ctrl.items == [] and ctrl.isLoading is False


def test_window_header_renders_with_ticker_controller(qapp):
    ctrl = _controller(qapp, SimpleNamespace(get_indicators=lambda: [MarketIndicator("USD/TRY", 40.0, "₺", 1.0)]))
    ctrl.refresh()
    from src.ui_qml.controllers.shell_controller import ShellController

    shell = ShellController(container=None)  # QML bağlamı sahibi olmadığı için referans tutulmalı
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty("marketTickerController", ctrl)
    engine.rootContext().setContextProperty("shellController", shell)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components/WindowHeader.qml")))
    if not component.isReady():
        pytest.fail("\n".join(e.toString() for e in component.errors()))

    item = component.create()

    assert item is not None and warnings == [], "\n".join(warnings)
