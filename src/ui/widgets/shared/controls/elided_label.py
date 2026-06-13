from src.qt_compat.qtwidgets import QLabel, QSizePolicy
from src.qt_compat.qtcore import Qt, QSize
from src.qt_compat.qtgui import QPainter, QFontMetrics

class ElidedLabel(QLabel):
    """
    A QLabel that elides its text (adds '...') if it doesn't fit in the available width,
    preventing it from expanding its parent layout unnecessarily.
    """
    def __init__(self, text="", parent=None, elide_candidates=None, minimum_width=20, preferred_width=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._text = text
        self._elide_candidates = list(elide_candidates or [])
        self._minimum_width = minimum_width
        self._preferred_width = preferred_width

    def setText(self, text):
        self._text = text
        super().setText(text)
        self.updateGeometry()
        self.update()

    def set_elide_candidates(self, candidates):
        self._elide_candidates = list(candidates or [])
        self.updateGeometry()
        self.update()

    def elided_text_for_width(self, width: int) -> str:
        metrics = QFontMetrics(self.font())
        if metrics.horizontalAdvance(self._text) <= width:
            return self._text

        for candidate in self._elide_candidates:
            if metrics.horizontalAdvance(candidate) <= width:
                return candidate

        fallback = self._elide_candidates[-1] if self._elide_candidates else self._text
        return metrics.elidedText(fallback, Qt.ElideRight, max(0, width))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawText(self.rect(), self.alignment(), self.elided_text_for_width(self.width()))

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        width = self._preferred_width
        if width is None:
            width = metrics.horizontalAdvance(self._text)
        return QSize(max(self._minimum_width, width), metrics.height())

    def minimumSizeHint(self):
        metrics = QFontMetrics(self.font())
        return QSize(self._minimum_width, metrics.height())
