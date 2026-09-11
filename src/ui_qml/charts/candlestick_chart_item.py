"""
CandlestickChartItem — saf QML-native mum grafik (bkz. plan §7.3 Stock360View
Sekme 1, §7.4 v1 kapsamı). Geometri `candlestick_mapper.compute_candlestick_bars()`'e
delege edilir (saf, ayrı test edilir); bu sınıf sadece `QPainter` çizimiyle ilgilenir.
"""
from __future__ import annotations

from typing import List

from src.qt_compat.qtcore import Property, QLineF, QRectF, Signal
from src.qt_compat.qtgui import QColor, QPainter, QPen
from src.qt_compat.qtquick import QQuickPaintedItem
from src.ui_qml.charts.candlestick_mapper import OhlcBar, compute_candlestick_bars

_DEFAULT_BULLISH_COLOR = "#10B981"  # Profit (Green), bkz. plan §7.2
_DEFAULT_BEARISH_COLOR = "#EF4444"  # Loss (Red), bkz. plan §7.2


class CandlestickChartItem(QQuickPaintedItem):
    """QML'den `bars` (list<{open,high,low,close}>) ile beslenen mum grafiği."""

    barsChanged = Signal()
    bullishColorChanged = Signal()
    bearishColorChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._bars: List[OhlcBar] = []
        self._bullish_color = QColor(_DEFAULT_BULLISH_COLOR)
        self._bearish_color = QColor(_DEFAULT_BEARISH_COLOR)

    def getBars(self) -> List[dict]:
        return [
            {"open": b.open, "high": b.high, "low": b.low, "close": b.close}
            for b in self._bars
        ]

    def setBars(self, bars) -> None:
        self._bars = [
            OhlcBar(
                open=float(b["open"]), high=float(b["high"]),
                low=float(b["low"]), close=float(b["close"]),
            )
            for b in bars
        ]
        self.barsChanged.emit()
        self.update()

    bars = Property("QVariantList", getBars, setBars, notify=barsChanged)

    def getBullishColor(self) -> QColor:
        return self._bullish_color

    def setBullishColor(self, color) -> None:
        self._bullish_color = QColor(color)
        self.bullishColorChanged.emit()
        self.update()

    bullishColor = Property(QColor, getBullishColor, setBullishColor, notify=bullishColorChanged)

    def getBearishColor(self) -> QColor:
        return self._bearish_color

    def setBearishColor(self, color) -> None:
        self._bearish_color = QColor(color)
        self.bearishColorChanged.emit()
        self.update()

    bearishColor = Property(QColor, getBearishColor, setBearishColor, notify=bearishColorChanged)

    def paint(self, painter: QPainter) -> None:
        geometries = compute_candlestick_bars(self._bars, self.width(), self.height())
        if not geometries:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        for geometry in geometries:
            color = self._bullish_color if geometry.is_bullish else self._bearish_color
            painter.setPen(QPen(color, 1.0))
            painter.drawLine(QLineF(geometry.x_center, geometry.wick_top_y, geometry.x_center, geometry.wick_bottom_y))

            painter.setBrush(color)
            body_height = max(geometry.body_bottom_y - geometry.body_top_y, 1.0)
            body_rect = QRectF(
                geometry.x_center - geometry.bar_width / 2.0, geometry.body_top_y,
                geometry.bar_width, body_height,
            )
            painter.drawRect(body_rect)
