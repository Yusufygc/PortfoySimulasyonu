from __future__ import annotations

from PyQt5.QtCore import QEvent, QSize
from PyQt5.QtWidgets import QLabel


class IconLabel(QLabel):
    """QLabel that re-renders its SVG icon on QEvent.StyleChange (theme switches)."""

    def __init__(self, icon_name: str, color: str = "@COLOR_TEXT_PRIMARY", size: int = 24, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._color = color
        self._size = size
        self._refresh()

    def _refresh(self):
        from src.ui.core.icon_manager import IconManager
        icon = IconManager.get_icon(self._icon_name, color=self._color, size=QSize(self._size, self._size))
        self.setPixmap(icon.pixmap(self._size, self._size))

    def changeEvent(self, event):
        if event.type() == QEvent.StyleChange:
            self._refresh()
        super().changeEvent(event)
