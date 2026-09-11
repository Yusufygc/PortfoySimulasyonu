"""
BarChartItem — saf QML-native bar grafiği (bkz. plan §7.4 v1 kapsamı,
AnalyticsView §7.3 madde 4). Geometri `bar_mapper.compute_bar_geometry()`'e
delege edilir (saf, ayrı test edilir); bu sınıf sadece `QPainter` çizimiyle
ilgilenir (`CandlestickChartItem` ile aynı desen).
"""
from __future__ import annotations

from typing import List

from src.qt_compat.qtcore import Property, QRectF, Signal
from src.qt_compat.qtgui import QColor, QPainter
from src.qt_compat.qtquick import QQuickPaintedItem
from src.ui_qml.charts.bar_mapper import compute_bar_geometry

_DEFAULT_POSITIVE_COLOR = "#10B981"  # Profit (Green), bkz. plan §7.2
_DEFAULT_NEGATIVE_COLOR = "#EF4444"  # Loss (Red), bkz. plan §7.2


class BarChartItem(QQuickPaintedItem):
    """QML'den `values` (list<real>) ile beslenen dikey bar grafiği (sıfır çizgili)."""

    valuesChanged = Signal()
    positiveColorChanged = Signal()
    negativeColorChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values: List[float] = []
        self._positive_color = QColor(_DEFAULT_POSITIVE_COLOR)
        self._negative_color = QColor(_DEFAULT_NEGATIVE_COLOR)

    def getValues(self) -> List[float]:
        return list(self._values)

    def setValues(self, values) -> None:
        self._values = [float(v) for v in values]
        self.valuesChanged.emit()
        self.update()

    values = Property("QVariantList", getValues, setValues, notify=valuesChanged)

    def getPositiveColor(self) -> QColor:
        return self._positive_color

    def setPositiveColor(self, color) -> None:
        self._positive_color = QColor(color)
        self.positiveColorChanged.emit()
        self.update()

    positiveColor = Property(QColor, getPositiveColor, setPositiveColor, notify=positiveColorChanged)

    def getNegativeColor(self) -> QColor:
        return self._negative_color

    def setNegativeColor(self, color) -> None:
        self._negative_color = QColor(color)
        self.negativeColorChanged.emit()
        self.update()

    negativeColor = Property(QColor, getNegativeColor, setNegativeColor, notify=negativeColorChanged)

    def paint(self, painter: QPainter) -> None:
        geometries = compute_bar_geometry(self._values, self.width(), self.height())
        if not geometries:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        for geometry in geometries:
            color = self._positive_color if geometry.is_positive else self._negative_color
            painter.setBrush(color)
            painter.setPen(QColor(0, 0, 0, 0))
            bar_height = max(geometry.bar_bottom_y - geometry.bar_top_y, 1.0)
            rect = QRectF(
                geometry.x_center - geometry.bar_width / 2.0, geometry.bar_top_y,
                geometry.bar_width, bar_height,
            )
            painter.drawRect(rect)
