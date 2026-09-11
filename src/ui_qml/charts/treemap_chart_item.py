"""
TreemapChartItem — saf QML-native treemap (bkz. plan §7.3 madde 6, §7.4,
AnalyticsView d4). Geometri `treemap_mapper.compute_treemap_rects()`'e delege
edilir (saf, ayrı test edilir); bu sınıf `QPainter` çizimiyle ilgilenir.

Diğer chart tiplerinden fark: hücreler alan bakımından çok farklı boyutlarda
olduğundan (küçük pozisyonlar küçük dikdörtgen) etiket/değer OKUNABİLİRLİK
için doğrudan hücrenin üstüne yazılır (`ScatterChartItem`'daki "canvas'a metin
yazma" kaçınma deseninin istisnası — treemap'in kendisi bir etiketli alan
haritasıdır, ayrı bir lejant anlamsız olur).

Renk: `value` (getiri %) işaretine göre kırmızı/yeşil arası doygunluk skalası
— AnalyticsView.qml'deki aylık ısı haritası `heatColor()` fonksiyonuyla aynı
görsel dil (±%15 doygunluk sınırı).
"""
from __future__ import annotations

from typing import List

from src.qt_compat.qtcore import Property, QRectF, Signal, Qt
from src.qt_compat.qtgui import QColor, QPainter, QPen
from src.qt_compat.qtquick import QQuickPaintedItem
from src.ui_qml.charts.treemap_mapper import compute_treemap_rects

_SATURATION_CAP_PCT = 15.0
_BORDER_COLOR = "#0B0F19"  # Background, bkz. plan §7.2 — hücreleri birbirinden ayırır
_NEUTRAL_COLOR = "#26354A"  # value=0 civarı, bkz. plan §7.2 Surface tonu


def _color_for_value(value: float) -> QColor:
    t = max(-1.0, min(1.0, value / _SATURATION_CAP_PCT))
    if t >= 0:
        return QColor.fromRgbF(0.06, 0.15 + 0.7 * t, 0.35, 1.0)
    return QColor.fromRgbF(0.15 + 0.7 * (-t), 0.08, 0.10, 1.0)


class TreemapChartItem(QQuickPaintedItem):
    """QML'den `items` (list<{label,weight,value}>) ile beslenen squarified treemap."""

    itemsChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: List[dict] = []

    def getItems(self) -> List[dict]:
        return [dict(item) for item in self._items]

    def setItems(self, items) -> None:
        self._items = [
            {"label": str(item["label"]), "weight": float(item["weight"]), "value": float(item["value"])}
            for item in items
        ]
        self.itemsChanged.emit()
        self.update()

    items = Property("QVariantList", getItems, setItems, notify=itemsChanged)

    def paint(self, painter: QPainter) -> None:
        triples = [(item["label"], item["weight"], item["value"]) for item in self._items]
        rects = compute_treemap_rects(triples, self.width(), self.height())
        if not rects:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        for rect in rects:
            color = _color_for_value(rect.value) if rect.value != 0 else QColor(_NEUTRAL_COLOR)
            painter.setBrush(color)
            painter.setPen(QPen(QColor(_BORDER_COLOR), 1.5))
            geometry = QRectF(rect.x, rect.y, rect.width, rect.height)
            painter.drawRect(geometry)

            if rect.width < 24 or rect.height < 18:
                continue  # çok küçük hücrede metin taşar, okunaksız olur — atlanır
            painter.setPen(QColor("#E5E7EB"))
            label_text = f"{rect.label}\n{rect.value:+.1f}%"
            painter.drawText(geometry, Qt.AlignCenter, label_text)
