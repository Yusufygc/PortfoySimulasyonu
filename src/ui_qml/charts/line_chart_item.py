"""
LineChartItem — saf QML-native çizgi/alan grafik bileşeni (bkz. plan §7.4/§9.4 d0 POC).

`QQuickPaintedItem` alt sınıfı; `Qt Charts` (GPLv3 lisans riski) ve `pyqtgraph`
(QQuickWidget hibrit, mimari saflık ihlali) yerine seçilen mimarinin ilk POC'u.
Nokta/koordinat hesabı `series_mapper.map_series_to_points()`'e delege edilir
(saf, Qt'siz, ayrı test edilir) — bu sınıf sadece QPainter çizimiyle ilgilenir.

Opsiyonel `values2`: MACD hattı + sinyal hattı gibi aynı y-ölçeğinde çizilmesi
gereken ikinci bir seri için (bkz. Stock360View §7.3 Sekme 1). Ortak min/max,
iki serinin birleşiminden hesaplanır — aksi halde her seri kendi aralığına göre
bağımsız normalize olur ve aralarındaki gerçek fark görsel olarak bozulur.
"""
from __future__ import annotations

from typing import List, Optional

from src.qt_compat.qtcore import Property, Signal
from src.qt_compat.qtgui import QColor, QPainter, QPainterPath, QPen
from src.qt_compat.qtquick import QQuickPaintedItem
from src.ui_qml.charts.series_mapper import map_series_to_points

_DEFAULT_LINE_COLOR = "#3B82F6"    # Primary Accent, bkz. plan §7.2 Tasarım Dili
_DEFAULT_LINE2_COLOR = "#F59E0B"   # ikincil seri (örn. MACD sinyal hattı)
_DEFAULT_LINE_WIDTH = 2.0


class LineChartItem(QQuickPaintedItem):
    """QML'den `values` (list<real>) ve opsiyonel `values2` ile beslenen çizgi grafiği."""

    valuesChanged = Signal()
    values2Changed = Signal()
    lineColorChanged = Signal()
    lineColor2Changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._values: List[float] = []
        self._values2: List[float] = []
        self._line_color = QColor(_DEFAULT_LINE_COLOR)
        self._line_color2 = QColor(_DEFAULT_LINE2_COLOR)

    def getValues(self) -> List[float]:
        return list(self._values)

    def setValues(self, values) -> None:
        self._values = [float(v) for v in values]
        self.valuesChanged.emit()
        self.update()

    values = Property("QVariantList", getValues, setValues, notify=valuesChanged)

    def getValues2(self) -> List[float]:
        return list(self._values2)

    def setValues2(self, values) -> None:
        self._values2 = [float(v) for v in values]
        self.values2Changed.emit()
        self.update()

    values2 = Property("QVariantList", getValues2, setValues2, notify=values2Changed)

    def getLineColor(self) -> QColor:
        return self._line_color

    def setLineColor(self, color) -> None:
        self._line_color = QColor(color)
        self.lineColorChanged.emit()
        self.update()

    lineColor = Property(QColor, getLineColor, setLineColor, notify=lineColorChanged)

    def getLineColor2(self) -> QColor:
        return self._line_color2

    def setLineColor2(self, color) -> None:
        self._line_color2 = QColor(color)
        self.lineColor2Changed.emit()
        self.update()

    lineColor2 = Property(QColor, getLineColor2, setLineColor2, notify=lineColor2Changed)

    def paint(self, painter: QPainter) -> None:
        combined = self._values + self._values2
        bounds = (min(combined), max(combined)) if combined else None

        painter.setRenderHint(QPainter.Antialiasing, True)
        self._paint_series(painter, self._values, self._line_color, bounds)
        self._paint_series(painter, self._values2, self._line_color2, bounds)

    def _paint_series(self, painter: QPainter, values: List[float], color: QColor, bounds: Optional[tuple]) -> None:
        points = map_series_to_points(values, self.width(), self.height(), value_bounds=bounds)
        if len(points) < 2:
            return

        pen = QPen(color)
        pen.setWidthF(_DEFAULT_LINE_WIDTH)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(*points[0])
        for x, y in points[1:]:
            path.lineTo(x, y)
        painter.drawPath(path)
