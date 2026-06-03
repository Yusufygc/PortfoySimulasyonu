from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPainter, QFontMetrics

class ElidedLabel(QLabel):
    """
    A QLabel that elides its text (adds '...') if it doesn't fit in the available width,
    preventing it from expanding its parent layout unnecessarily.
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self._text = text

    def setText(self, text):
        self._text = text
        super().setText(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._text, Qt.ElideRight, self.width())
        painter.drawText(self.rect(), self.alignment(), elided)

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        return QSize(metrics.width(self._text), metrics.height())

    def minimumSizeHint(self):
        metrics = QFontMetrics(self.font())
        return QSize(20, metrics.height()) # Allow shrinking
