"""CandlestickChartItem — QQuickPaintedItem entegrasyon duman testleri (bkz. plan §7.3/§7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.candlestick_chart_item import CandlestickChartItem


@pytest.fixture
def chart_item(qapp):
    item = CandlestickChartItem()
    item.setWidth(120.0)
    item.setHeight(80.0)
    return item


def _has_non_transparent_pixel(image) -> bool:
    from src.qt_compat.qtgui import qAlpha

    for x in range(image.width()):
        for y in range(image.height()):
            if qAlpha(image.pixel(x, y)) > 0:
                return True
    return False


_SAMPLE_BARS = [
    {"open": 10.0, "high": 12.0, "low": 8.0, "close": 11.0},
    {"open": 11.0, "high": 13.0, "low": 9.0, "close": 9.5},
]


class TestBarsProperty:
    def test_set_bars_updates_getter(self, chart_item):
        chart_item.setBars(_SAMPLE_BARS)
        assert chart_item.getBars() == _SAMPLE_BARS

    def test_set_bars_emits_signal(self, chart_item):
        received = []
        chart_item.barsChanged.connect(lambda: received.append(True))

        chart_item.setBars(_SAMPLE_BARS)

        assert received == [True]

    def test_default_bars_are_empty(self, chart_item):
        assert chart_item.getBars() == []


class TestColorProperties:
    def test_default_bullish_color_matches_theme_profit(self, chart_item):
        assert chart_item.getBullishColor().name().lower() == "#10b981"

    def test_default_bearish_color_matches_theme_loss(self, chart_item):
        assert chart_item.getBearishColor().name().lower() == "#ef4444"

    def test_set_bullish_color_updates_getter_and_emits_signal(self, chart_item):
        received = []
        chart_item.bullishColorChanged.connect(lambda: received.append(True))

        chart_item.setBullishColor("#3B82F6")

        assert chart_item.getBullishColor().name().lower() == "#3b82f6"
        assert received == [True]


class TestPaint:
    def test_paint_with_no_bars_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        image = QImage(120, 80, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)

    def test_paint_with_bars_draws_visible_candles(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setBars(_SAMPLE_BARS)
        image = QImage(120, 80, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)
