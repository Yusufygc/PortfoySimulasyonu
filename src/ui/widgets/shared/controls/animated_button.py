# src/ui/widgets/shared/controls/animated_button.py
"""
AnimatedButton — Etkileşimli Buton Widget'ı

Hover/press görsel geri bildirimi QSS pseudo-state'leri (`:hover`, `:pressed`)
ile sağlanır; bu yüzden tüm temalarda (light/dark) buton zemini doğru render
edilir.

Tarihsel not:
    Daha önce hover/press için QGraphicsOpacityEffect + QPropertyAnimation
    kullanılıyordu. Ancak grafik efekt butona bağlıyken QPushButton offscreen
    buffer'a render ediliyor ve light temada QSS `background-color` kaybolup
    buton beyaz görünüyordu. Efekti animasyon sırasında bağla/ayır denemeleri
    `RuntimeError: wrapped C/C++ object ... deleted` çökmelerine yol açtı.
    Sade ve sağlam çözüm: grafik efekti bırak, görsel feedback'i QSS'e taşı.

Kullanım:
    btn = AnimatedButton("Optimize Et")
    btn.setProperty("cssClass", "primaryButtonLarge")
    btn.setIconName("zap")
"""
from __future__ import annotations

from src.qt_compat.qtwidgets import QPushButton
from src.qt_compat.qtcore import Qt, QEvent


class AnimatedButton(QPushButton):
    """
    Pointer cursor ve token tabanlı ikon desteği olan QPushButton.
    setProperty("cssClass", ...) ile QSS'den stillendirilir; hover/press
    geri bildirimi QSS pseudo-state'leri tarafından yönetilir.
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def setIconName(self, name: str, color: str = "@COLOR_TEXT_WHITE", size: int = 18):
        """İkon adıyla IconManager üzerinden ikon set eder."""
        self._icon_name = name
        self._icon_color = color
        self._icon_size = size
        self._apply_icon()

    def _apply_icon(self):
        if not hasattr(self, "_icon_name"):
            return
            
        from src.ui.theme_manager import ThemeManager
        current_theme = ThemeManager.current_theme_id()
            
        from src.ui.core.icon_manager import IconManager
        from src.qt_compat.qtcore import QSize
        self.setIcon(IconManager.get_icon(self._icon_name, color=self._icon_color, size=QSize(self._icon_size, self._icon_size)))
        self._last_applied_theme = current_theme

    def changeEvent(self, event) -> None:
        # Tema değişiminde ikonu yeni token rengiyle yeniden üret.
        if event.type() == QEvent.StyleChange and hasattr(self, "_icon_name"):
            self._apply_icon()
        super().changeEvent(event)
