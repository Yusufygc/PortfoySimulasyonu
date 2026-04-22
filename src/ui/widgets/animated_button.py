# src/ui/widgets/animated_button.py
"""
AnimatedButton — Mikro Etkileşimli Buton Widget'ı

PyQt5'te CSS `transition` desteklenmediğinden, hover/press
efektleri QGraphicsOpacityEffect + QPropertyAnimation ile sağlanır.

Kullanım:
    btn = AnimatedButton("🚀 Optimize Et")
    btn.setProperty("cssClass", "primaryButtonLarge")

Özellikler:
    - Hover: Yumuşak opaklık artışı (0.85 → 1.0)
    - Press: Anlık opacity baskısı (1.0 → 0.7 → 1.0)
    - Performans: Animasyon süresi kısa tutuldu (150ms hover, 80ms press)
    - Geriye dönük uyum: QPushButton'ın tüm API'sini miras alır
"""
from __future__ import annotations

from PyQt5.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    QSequentialAnimationGroup, pyqtProperty,
)


class AnimatedButton(QPushButton):
    """
    Hover ve press animasyonları olan QPushButton.
    setProperty("cssClass", ...) ile QSS'den normal buton gibi stillendirilir.
    """

    _HOVER_DURATION  = 150   # ms — hover fade-in/out
    _PRESS_DOWN_MS   = 60    # ms — tıklama baskısı
    _PRESS_UP_MS     = 100   # ms — bırakma geri dönüşü
    _OPACITY_NORMAL  = 1.0
    _OPACITY_HOVER   = 0.92  # Hover hafif mat
    _OPACITY_PRESSED = 0.65  # Press belirgin baskı

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

        # Opacity efekti
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(self._OPACITY_NORMAL)
        self.setGraphicsEffect(self._effect)

        # Animasyonlar
        self._hover_anim = self._make_anim(self._HOVER_DURATION)
        self._press_group = self._make_press_group()

    # ------------------------------------------------------------------
    # Animasyon oluşturucular
    # ------------------------------------------------------------------

    def _make_anim(self, duration: int) -> QPropertyAnimation:
        anim = QPropertyAnimation(self._effect, b"opacity")
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        return anim

    def _make_press_group(self) -> QSequentialAnimationGroup:
        """Baskı → bırakış animasyon zinciri."""
        group = QSequentialAnimationGroup(self)

        down = QPropertyAnimation(self._effect, b"opacity")
        down.setDuration(self._PRESS_DOWN_MS)
        down.setStartValue(self._OPACITY_NORMAL)
        down.setEndValue(self._OPACITY_PRESSED)
        down.setEasingCurve(QEasingCurve.OutQuart)

        up = QPropertyAnimation(self._effect, b"opacity")
        up.setDuration(self._PRESS_UP_MS)
        up.setStartValue(self._OPACITY_PRESSED)
        up.setEndValue(self._OPACITY_NORMAL)
        up.setEasingCurve(QEasingCurve.OutBounce)

        group.addAnimation(down)
        group.addAnimation(up)
        return group

    # ------------------------------------------------------------------
    # Qt Events
    # ------------------------------------------------------------------

    def enterEvent(self, event) -> None:
        """Fare üzerine gelince mat → parlak geçiş."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._effect.opacity())
        self._hover_anim.setEndValue(self._OPACITY_HOVER)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Fare ayrılınca normale dön."""
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._effect.opacity())
        self._hover_anim.setEndValue(self._OPACITY_NORMAL)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        """Tıklamada baskı efekti."""
        if event.button() == Qt.LeftButton:
            self._hover_anim.stop()
            self._press_group.stop()
            self._press_group.start()
        super().mousePressEvent(event)
