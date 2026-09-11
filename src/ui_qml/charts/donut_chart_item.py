"""
DonutChartItem — varlık dağılımı için saf QML-native donut/pasta grafik (bkz. plan
§7.3 DashboardView, §7.4 v1 kapsamı genişletmesi). `LineChartItem` ile aynı desen:
açı hesabı `donut_mapper.compute_donut_segments()`'e delege edilir (saf, ayrı test
edilir), bu sınıf sadece `QPainter` çizimiyle ilgilenir.
"""
from __future__ import annotations

from typing import List

from src.qt_compat.qtcore import Property, QRectF, Qt, Signal
from src.qt_compat.qtgui import QColor, QPainter
from src.qt_compat.qtquick import QQuickPaintedItem
from src.ui_qml.charts.donut_mapper import compute_donut_segments

# Modern Fintech Dark paleti (§7.2) + ek kategorik renkler (varlık sayısı 5'i geçebilir).
_PALETTE = (
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#14B8A6", "#F97316",
)
_INNER_HOLE_RATIO = 0.55  # donut deliğinin dış çapa oranı


class DonutChartItem(QQuickPaintedItem):
    """QML'den `weights` (list<real>, yüzde) ile beslenen donut grafik."""

    weightsChanged = Signal()
    holeColorChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._weights: List[float] = []
        self._hole_color = QColor("#0B0F19")  # Background, bkz. §7.2

    def getWeights(self) -> List[float]:
        return list(self._weights)

    def setWeights(self, weights) -> None:
        self._weights = [float(w) for w in weights]
        self.weightsChanged.emit()
        self.update()

    weights = Property("QVariantList", getWeights, setWeights, notify=weightsChanged)

    def getHoleColor(self) -> QColor:
        return self._hole_color

    def setHoleColor(self, color) -> None:
        self._hole_color = QColor(color)
        self.holeColorChanged.emit()
        self.update()

    holeColor = Property(QColor, getHoleColor, setHoleColor, notify=holeColorChanged)

    def paint(self, painter: QPainter) -> None:
        segments = compute_donut_segments(self._weights)
        if not segments:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        side = min(self.width(), self.height())
        outer_rect = QRectF((self.width() - side) / 2.0, (self.height() - side) / 2.0, side, side)

        painter.setPen(Qt.NoPen)
        for index, (start_angle, span_angle) in enumerate(segments):
            painter.setBrush(QColor(_PALETTE[index % len(_PALETTE)]))
            # QPainter açıları 1/16 derece biriminde, saatin tersine (CCW) pozitif —
            # saat yönünde ilerleyen donut_mapper çıktısını negatife çevirerek eşliyoruz.
            painter.drawPie(outer_rect, int(-start_angle * 16), int(-span_angle * 16))

        inner_side = side * _INNER_HOLE_RATIO
        inner_rect = QRectF(
            (self.width() - inner_side) / 2.0, (self.height() - inner_side) / 2.0, inner_side, inner_side,
        )
        painter.setBrush(self._hole_color)
        painter.drawEllipse(inner_rect)
