"""Hisse Detay > Grafik: ortalama maliyet çizgisi (chart payload ve şablon)."""
from __future__ import annotations

import json
from pathlib import Path

from src.ui_qml.controllers.chart_controller import ChartController

TEMPLATE = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "assets" / "templates" / "tradingview_chart.html"


def _payloads(ctrl):
    received = []
    ctrl.chartDataLoaded.connect(lambda ticker, payload: received.append((ticker, json.loads(payload))))
    return received


def test_chart_payload_carries_average_cost_for_the_position_ticker(qapp):
    ctrl = ChartController(container=None)
    received = _payloads(ctrl)

    ctrl.loadTickerWithCost("THYAO.IS", 123.45)

    ticker, payload = received[-1]
    assert payload["ticker"] == "THYAO" and payload["avgCost"] == 123.45


def test_plain_load_and_other_tickers_have_no_cost_line(qapp):
    ctrl = ChartController(container=None)
    received = _payloads(ctrl)
    ctrl.loadTickerWithCost("THYAO", 100.0)

    ctrl.loadTicker("THYAO")  # sıradan yükleme maliyet çizgisini temizler
    assert received[-1][1]["avgCost"] is None

    ctrl.loadTickerWithCost("THYAO", 100.0)
    ctrl.loadTickerWithCost("ASELS", 0.0)  # maliyet yok
    assert received[-1][1]["avgCost"] is None


def test_timeframe_change_keeps_average_cost(qapp):
    ctrl = ChartController(container=None)
    received = _payloads(ctrl)
    ctrl.loadTickerWithCost("THYAO", 100.0)

    ctrl.setTimeframe("1W")

    assert received[-1][1]["timeframe"] == "1W" and received[-1][1]["avgCost"] == 100.0


def test_chart_template_draws_and_clears_the_average_cost_line():
    html = TEMPLATE.read_text(encoding="utf-8")

    assert "function renderAverageCostLine()" in html
    assert "createPriceLine" in html and "Ort. Maliyet" in html
    assert "removePriceLine(avgCostLine)" in html
    assert html.count("renderAverageCostLine();") >= 1
