"""ScatterChartItem — QQuickPaintedItem entegrasyon duman testleri (bkz. plan §7.3/§7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.scatter_chart_item import ScatterChartItem


@pytest.fixture
def chart_item(qapp):
    item = ScatterChartItem()
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


class TestValuesProperties:
    def test_set_values_x_updates_getter(self, chart_item):
        chart_item.setValuesX([1.0, 2.0])
        assert chart_item.getValuesX() == [1.0, 2.0]

    def test_set_values_y_updates_getter(self, chart_item):
        chart_item.setValuesY([3.0, 4.0])
        assert chart_item.getValuesY() == [3.0, 4.0]

    def test_set_values_x_emits_signal(self, chart_item):
        received = []
        chart_item.valuesXChanged.connect(lambda: received.append(True))

        chart_item.setValuesX([1.0])

        assert received == [True]

    def test_defaults_are_empty(self, chart_item):
        assert chart_item.getValuesX() == []
        assert chart_item.getValuesY() == []


class TestColorProperty:
    def test_default_point_color_matches_theme_primary_accent(self, chart_item):
        assert chart_item.getPointColor().name().lower() == "#3b82f6"

    def test_set_point_color_updates_getter_and_emits_signal(self, chart_item):
        received = []
        chart_item.pointColorChanged.connect(lambda: received.append(True))

        chart_item.setPointColor("#EF4444")

        assert chart_item.getPointColor().name().lower() == "#ef4444"
        assert received == [True]


class TestPaint:
    def test_paint_with_no_points_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        image = QImage(120, 80, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)

    def test_paint_with_points_draws_visible_dots(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setValuesX([10.0, 20.0, 30.0])
        chart_item.setValuesY([1.0, 5.0, 2.0])
        image = QImage(120, 80, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)
