"""
Faz 3 — TradingView Teknik Analiz Laboratuvarı Testleri:
Çoklu zaman dilimleri (1D, 1W, 1M), İndikatörler (SMA, EMA, BB, RSI, MACD),
Golden/Death cross tespitleri ve grafik tipi yönetimi.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.ui_qml.controllers.chart_controller import ChartController
from src.application.container import AppContainer


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_chart_controller_initialization(qapp):
    controller = ChartController()
    assert controller.currentTicker != ""
    assert controller.currentTimeframe == "1D"
    assert controller.currentChartType == "candle"
    assert "1D" in controller.timeframes
    assert "1W" in controller.timeframes
    assert "1M" in controller.timeframes


def test_chart_controller_timeframe_resampling(qapp):
    container = AppContainer()
    controller = ChartController(container=container)

    # 1D yükleme
    events = []
    controller.chartDataLoaded.connect(lambda t, p: events.append((t, p)))
    controller.loadTicker("OBAMS.IS")

    assert len(events) == 1
    ticker, payload_str = events[0]
    assert ticker == "OBAMS.IS"
    data_1d = json.loads(payload_str)
    assert len(data_1d["candles"]) > 0

    # 1W (Haftalık) yükleme
    events.clear()
    controller.setTimeframe("1W")
    assert len(events) == 1
    data_1w = json.loads(events[0][1])
    assert len(data_1w["candles"]) > 0
    # Haftalık mum sayısı günlük mum sayısından az olmalıdır
    assert len(data_1w["candles"]) < len(data_1d["candles"])

    # 1M (Aylık) yükleme
    events.clear()
    controller.setTimeframe("1M")
    assert len(events) == 1
    data_1m = json.loads(events[0][1])
    assert len(data_1m["candles"]) > 0
    # Aylık mum sayısı haftalık mum sayısından az olmalıdır
    assert len(data_1m["candles"]) < len(data_1w["candles"])


def test_chart_controller_technical_indicators_payload(qapp):
    container = AppContainer()
    controller = ChartController(container=container)

    events = []
    controller.chartDataLoaded.connect(lambda t, p: events.append((t, p)))
    controller.loadTicker("OBAMS.IS")

    assert len(events) == 1
    payload = json.loads(events[0][1])

    # İndikatör alanları
    assert "candles" in payload
    assert "volumes" in payload
    assert "sma20" in payload
    assert "sma50" in payload
    assert "sma200" in payload
    assert "ema20" in payload
    assert "bb" in payload
    assert "upper" in payload["bb"]
    assert "middle" in payload["bb"]
    assert "lower" in payload["bb"]
    assert "rsi" in payload
    assert "macd" in payload
    assert "macd" in payload["macd"]
    assert "signal" in payload["macd"]
    assert "hist" in payload["macd"]
    assert "markers" in payload

    # Mum verileri formatı
    first_candle = payload["candles"][0]
    assert "time" in first_candle
    assert "open" in first_candle
    assert "high" in first_candle
    assert "low" in first_candle
    assert "close" in first_candle


def test_chart_controller_indicator_toggles(qapp):
    controller = ChartController()
    assert controller.isIndicatorActive("sma50") is False
    assert "sma50" not in controller.activeIndicators

    # Açma (True)
    controller.toggleIndicator("sma50", True)
    assert controller.isIndicatorActive("sma50") is True
    assert "sma50" in controller.activeIndicators

    # Kapatma (False)
    controller.toggleIndicator("sma50", False)
    assert controller.isIndicatorActive("sma50") is False
    assert "sma50" not in controller.activeIndicators

    # Tek parametreli toggle ile Açma
    controller.toggleIndicator("sma50")
    assert controller.isIndicatorActive("sma50") is True
    assert "sma50" in controller.activeIndicators

    # Tek parametreli toggle ile Geri Kapatma
    controller.toggleIndicator("sma50")
    assert controller.isIndicatorActive("sma50") is False
    assert "sma50" not in controller.activeIndicators

    # Grafik tipi değişimi
    controller.setChartType("line")
    assert controller.currentChartType == "line"
    controller.setChartType("candle")
    assert controller.currentChartType == "candle"
