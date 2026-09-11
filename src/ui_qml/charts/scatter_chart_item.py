"""
ScatterChartItem — saf QML-native risk/getiri saçılım grafiği (bkz. plan §7.4
v1 kapsamı, AnalyticsView §7.3 madde 5). Geometri
`scatter_mapper.compute_scatter_points()`'e delege edilir (saf, ayrı test
edilir); bu sınıf sadece nokta çizimiyle ilgilenir. Etiketler (varlık adı)
canvas üzerine YAZILMAZ — QML tarafında ayrı bir metin lejantı gösterilir
(bkz. AnalyticsView.qml), `CandlestickChartItem`'daki gibi metinsiz çizim deseni.
"""
from __future__ import annotations

from typing import List

from src.qt_compat.qtcore import Property, QRectF, Signal
from src.qt_compat.qtgui import QColor, QPainter
from src.qt_compat.qtquick import QQuickPaintedItem
from src.ui_qml.charts.scatter_mapper import compute_scatter_points

_DEFAULT_POINT_COLOR = "#3B82F6"  # Primary Accent, bkz. plan §7.2
_DEFAULT_POINT_RADIUS = 5.0


class ScatterChartItem(QQuickPaintedItem):
    """QML'den paralel `valuesX`/`valuesY` (list<real>) ile beslenen saçılım grafiği."""

    valuesXChanged = Signal()
    valuesYChanged = Signal()
    pointColorChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values_x: List[float] = []
        self._values_y: List[float] = []
        self._point_color = QColor(_DEFAULT_POINT_COLOR)

    def getValuesX(self) -> List[float]:
        return list(self._values_x)

    def setValuesX(self, values) -> None:
        self._values_x = [float(v) for v in values]
        self.valuesXChanged.emit()
        self.update()

    valuesX = Property("QVariantList", getValuesX, setValuesX, notify=valuesXChanged)

    def getValuesY(self) -> List[float]:
        return list(self._values_y)

    def setValuesY(self, values) -> None:
        self._values_y = [float(v) for v in values]
        self.valuesYChanged.emit()
        self.update()

    valuesY = Property("QVariantList", getValuesY, setValuesY, notify=valuesYChanged)

    def getPointColor(self) -> QColor:
        return self._point_color

    def setPointColor(self, color) -> None:
        self._point_color = QColor(color)
        self.pointColorChanged.emit()
        self.update()

    pointColor = Property(QColor, getPointColor, setPointColor, notify=pointColorChanged)

    def paint(self, painter: QPainter) -> None:
        points = compute_scatter_points(self._values_x, self._values_y, self.width(), self.height())
        if not points:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(self._point_color)
        painter.setPen(QColor(0, 0, 0, 0))
        radius = _DEFAULT_POINT_RADIUS
        for x, y in points:
            painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2.0, radius * 2.0))
