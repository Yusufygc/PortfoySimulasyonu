"""DonutChartItem — QQuickPaintedItem entegrasyon duman testleri (bkz. plan §7.3/§7.4).

Görsel regresyon testi değildir — burada doğrulanan gerçek `QPainter` çiziminin
piksel bastığı, property set/notify'ın çalıştığı.
"""
from __future__ import annotations

import pytest

from src.ui_qml.charts.donut_chart_item import DonutChartItem


@pytest.fixture
def chart_item(qapp):
    item = DonutChartItem()
    item.setWidth(120.0)
    item.setHeight(120.0)
    return item


def _has_non_transparent_pixel(image) -> bool:
    from src.qt_compat.qtgui import qAlpha

    for x in range(image.width()):
        for y in range(image.height()):
            if qAlpha(image.pixel(x, y)) > 0:
                return True
    return False


class TestWeightsProperty:
    def test_set_weights_updates_getter(self, chart_item):
        chart_item.setWeights([50.0, 30.0, 20.0])
        assert chart_item.getWeights() == [50.0, 30.0, 20.0]

    def test_set_weights_emits_signal(self, chart_item):
        received = []
        chart_item.weightsChanged.connect(lambda: received.append(True))

        chart_item.setWeights([1.0, 2.0])

        assert received == [True]

    def test_default_weights_are_empty(self, chart_item):
        assert chart_item.getWeights() == []


class TestHoleColorProperty:
    def test_default_hole_color_matches_theme_background(self, chart_item):
        assert chart_item.getHoleColor().name().lower() == "#0b0f19"

    def test_set_hole_color_updates_getter_and_emits_signal(self, chart_item):
        received = []
        chart_item.holeColorChanged.connect(lambda: received.append(True))

        chart_item.setHoleColor("#151D2C")

        assert chart_item.getHoleColor().name().lower() == "#151d2c"
        assert received == [True]


class TestPaint:
    def test_paint_with_no_weights_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        image = QImage(120, 120, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)

    def test_paint_with_weights_draws_visible_segments(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setWeights([50.0, 30.0, 20.0])
        image = QImage(120, 120, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)
