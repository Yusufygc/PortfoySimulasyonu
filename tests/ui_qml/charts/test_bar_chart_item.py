"""BarChartItem — QQuickPaintedItem entegrasyon duman testleri (bkz. plan §7.3/§7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.bar_chart_item import BarChartItem


@pytest.fixture
def chart_item(qapp):
    item = BarChartItem()
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


class TestValuesProperty:
    def test_set_values_updates_getter(self, chart_item):
        chart_item.setValues([1.0, -2.0, 3.0])
        assert chart_item.getValues() == [1.0, -2.0, 3.0]

    def test_set_values_emits_signal(self, chart_item):
        received = []
        chart_item.valuesChanged.connect(lambda: received.append(True))

        chart_item.setValues([1.0])

        assert received == [True]

    def test_default_values_are_empty(self, chart_item):
        assert chart_item.getValues() == []


class TestColorProperties:
    def test_default_positive_color_matches_theme_profit(self, chart_item):
        assert chart_item.getPositiveColor().name().lower() == "#10b981"

    def test_default_negative_color_matches_theme_loss(self, chart_item):
        assert chart_item.getNegativeColor().name().lower() == "#ef4444"

    def test_set_negative_color_updates_getter_and_emits_signal(self, chart_item):
        received = []
        chart_item.negativeColorChanged.connect(lambda: received.append(True))

        chart_item.setNegativeColor("#3B82F6")

        assert chart_item.getNegativeColor().name().lower() == "#3b82f6"
        assert received == [True]


class TestPaint:
    def test_paint_with_no_values_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        image = QImage(120, 80, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)

    def test_paint_with_values_draws_visible_bars(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setValues([5.0, -3.0, 2.0])
        image = QImage(120, 80, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)
