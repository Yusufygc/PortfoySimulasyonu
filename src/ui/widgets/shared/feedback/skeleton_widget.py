# src/ui/widgets/shared/feedback/skeleton_widget.py
"""
SkeletonBlock — Shimmer yükleme animasyonu widget'ı.

Async veri yüklenirken kart içi placeholder olarak kullanılır.
Kullanım:
    block = SkeletonBlock(width=200, height=18)
    layout.addWidget(block)
    block.start()   # animasyonu başlat
    block.stop()    # animasyonu durdur ve gizle
"""
from __future__ import annotations

from src.qt_compat.qtwidgets import QWidget, QSizePolicy
from src.qt_compat.qtcore import QVariantAnimation, QEasingCurve, Qt
from src.qt_compat.qtgui import QPainter, QColor, QLinearGradient, QPainterPath


class SkeletonBlock(QWidget):
    """
    Soldan sağa kayan shimmer gradyanı çizen hafif bir widget.
    _anim_offset (0.0 → 1.0 döngü) gradient'in x konumunu kontrol eder.
    """

    def __init__(
        self,
        width: int = 120,
        height: int = 20,
        radius: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self._anim_offset: float = 0.0
        self.setFixedSize(width, height)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.valueChanged.connect(self._on_value_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self.show()
        if self._anim.state() != QVariantAnimation.State.Running:
            self._anim.start()

    def stop(self) -> None:
        self._anim.stop()
        self.hide()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_value_changed(self, value: float) -> None:
        self._anim_offset = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Arka plan rengi (tema token yok, genel gri kullan)
        base_color = QColor(128, 128, 128, 40)

        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, self._radius, self._radius)
        painter.fillPath(path, base_color)

        # Shimmer gradient — offset ile sola/sağa kayar
        offset = self._anim_offset
        grad_x_start = w * (offset * 2 - 0.5)
        grad_x_end = grad_x_start + w * 0.6

        gradient = QLinearGradient(grad_x_start, 0, grad_x_end, 0)
        shimmer = QColor(200, 200, 200, 80)
        transparent = QColor(200, 200, 200, 0)
        gradient.setColorAt(0.0, transparent)
        gradient.setColorAt(0.5, shimmer)
        gradient.setColorAt(1.0, transparent)

        painter.save()
        painter.setClipPath(path)
        painter.fillRect(0, 0, w, h, gradient)
        painter.restore()
        painter.end()
