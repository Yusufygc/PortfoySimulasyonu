"""TreemapChartItem — QQuickPaintedItem entegrasyon duman testleri (bkz. plan §7.3/§7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.treemap_chart_item import TreemapChartItem

_SAMPLE_ITEMS = [
    {"label": "AKBNK", "weight": 5.0, "value": 12.5},
    {"label": "THYAO", "weight": 3.0, "value": -8.2},
]


@pytest.fixture
def chart_item(qapp):
    item = TreemapChartItem()
    item.setWidth(200.0)
    item.setHeight(120.0)
    return item


def _has_non_transparent_pixel(image) -> bool:
    from src.qt_compat.qtgui import qAlpha

    for x in range(image.width()):
        for y in range(image.height()):
            if qAlpha(image.pixel(x, y)) > 0:
                return True
    return False


class TestItemsProperty:
    def test_set_items_updates_getter(self, chart_item):
        chart_item.setItems(_SAMPLE_ITEMS)
        assert chart_item.getItems() == _SAMPLE_ITEMS

    def test_set_items_emits_signal(self, chart_item):
        received = []
        chart_item.itemsChanged.connect(lambda: received.append(True))

        chart_item.setItems(_SAMPLE_ITEMS)

        assert received == [True]

    def test_default_items_are_empty(self, chart_item):
        assert chart_item.getItems() == []


class TestPaint:
    def test_paint_with_no_items_does_not_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        image = QImage(200, 120, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)

    def test_paint_with_items_draws_visible_cells(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setItems(_SAMPLE_ITEMS)
        image = QImage(200, 120, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert _has_non_transparent_pixel(image)

    def test_zero_weight_items_are_skipped_without_crash(self, chart_item):
        from src.qt_compat.qtgui import QImage, QPainter

        chart_item.setItems([{"label": "EMPTY", "weight": 0.0, "value": 0.0}])
        image = QImage(200, 120, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        chart_item.paint(painter)
        painter.end()

        assert not _has_non_transparent_pixel(image)
