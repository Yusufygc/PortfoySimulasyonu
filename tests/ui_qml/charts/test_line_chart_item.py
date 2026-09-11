"""LineChartItem — QQuickPaintedItem entegrasyon duman testleri (bkz. plan §9.4 d0 POC).

Görsel regresyon testi değildir (plan §7.4) — burada doğrulanan şey PySide6/QtQuick
entegrasyonunun gerçekten çalıştığı: property set/notify, ve `paint()`'in bir
QPainter üzerine gerçekten piksel bastığı.
"""
from __future__ import annotations

import pytest

from src.ui_qml.charts.line_chart_item import LineChartItem


@pytest.fixture
def chart_item(qapp):
    item = LineChartItem()
    item.setWidth(100.0)
    item.setHeight(50.0)
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
        chart_item.setValues([1.0, 2.0, 3.0])
        assert chart_item.getValues() == [1.0, 2.0, 3.0]

    def test_set_values_emits_signal(self, chart_item):
        received = []
        chart_item.valuesChanged.connect(lambda: received.append(True))

        chart_item.setValues([5.0, 6.0])

        assert received == [True]

    def test_default_values_are_empty(self, chart_item):
        assert chart_item.getValues() == []


class TestLineColorProperty:
    def test_default_line_color_matches_theme_accent(self, chart_item):
        # Primary Accent, bkz. plan §7.2 Tasarım Dili
        assert chart_item.getLineColor().name().lower() == "#3b82f6"

    def test_set_line_color_updates_getter_and_emits_signal(self, chart_item):
        received = []
        chart_item.lineColorChanged.connect(lambda: received.append(True))

        chart_item.setLineColor("#10B981")

        assert chart_item.getLineColor().name().lower() == "#10b981"
        assert received == [True]


class TestValues2Property:
    def test_set_values2_updates_getter(self, chart_item):
        chart_item.setValues2([7.0, 8.0])
        assert chart_item.getValues2() == [7.0, 8.0]

    def test_set_values2_emits_signal(self, chart_item):
        received = []
        chart_item.values2Changed.connect(lambda: received.append(True))

        chart_item.setValues2([1.0, 2.0])

        assert received == [True]

    def test_default_values2_are_empty(self, chart_item):
        assert chart_item.getValues2() == []

    def test_default_line_color2_differs_from_line_color(self, chart_item):
        assert chart_item.getLineColor2().name().lower() != chart_item.getLineColor().name().lower()

    def test_set_line_color2_updates_getter_and_emits_signal(self, chart_item):
        received = []
        chart_item.lineColor2Changed.connect(lambda: received.append(True))

        chart_item.setLineColor2("#8B5CF6")

        assert chart_item.getLineColor2().name().lower() == "#8b5cf6"
        assert received == [True]


class TestPaint:
    def test_paint_with_no_values_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        image = QImage(100, 50, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)

    def test_paint_with_series_draws_visible_line(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setValues([10.0, 40.0, 15.0, 50.0, 5.0])
        image = QImage(100, 50, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)

    def test_paint_with_only_values2_draws_visible_line(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setValues2([10.0, 40.0, 15.0, 50.0, 5.0])
        image = QImage(100, 50, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)

    def test_paint_with_both_series_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setValues([10.0, 40.0, 15.0])
        chart_item.setValues2([-5.0, 20.0, 0.0])
        image = QImage(100, 50, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)
