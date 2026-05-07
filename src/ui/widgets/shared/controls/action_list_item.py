from __future__ import annotations

from PyQt5.QtCore import Qt, QEvent, QSize, pyqtSignal
from PyQt5.QtWidgets import QAction, QHBoxLayout, QLabel, QMenu, QToolButton, QWidget

from src.ui.core.icon_manager import IconManager


class ActionListItem(QWidget):
    """List row with a trailing three-dot actions menu."""

    selected = pyqtSignal()
    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("actionListItem")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self.setStyleSheet("QWidget#actionListItem { background: transparent; border: none; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.label = QLabel(text)
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.label.setAutoFillBackground(False)
        # Let QSS cascade handle the color (base/labels.qss: QLabel { color: @COLOR_TEXT_BODY })
        self.label.setStyleSheet(
            "QLabel { background: transparent; border: none; font-size: 15px; }"
        )
        layout.addWidget(self.label, 1)

        self.menu_button = QToolButton()
        self.menu_button.setIconSize(QSize(20, 20))
        self.menu_button.setFixedSize(28, 28)
        self.menu_button.setCursor(Qt.PointingHandCursor)
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.menu_button.setToolTip("Islemler")
        self.menu_button.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: rgba(148, 163, 184, 0.18);
            }
            QToolButton::menu-indicator { image: none; width: 0; }
            """
        )
        self._refresh_menu_icon()

        self._action_edit = QAction("Düzenle", self)
        self._action_delete = QAction("Sil", self)
        self._action_edit.triggered.connect(lambda checked=False: self.edit_requested.emit())
        self._action_delete.triggered.connect(lambda checked=False: self.delete_requested.emit())
        self._refresh_action_icons()

        menu = QMenu(self.menu_button)
        menu.addAction(self._action_edit)
        menu.addAction(self._action_delete)
        self.menu_button.setMenu(menu)

        layout.addWidget(self.menu_button, 0, Qt.AlignVCenter)

    def _refresh_menu_icon(self):
        self.menu_button.setIcon(IconManager.get_icon("ellipsis", color="@COLOR_TEXT_PRIMARY", size=QSize(20, 20)))

    def _refresh_action_icons(self):
        self._action_edit.setIcon(IconManager.get_icon("pencil", color="@COLOR_TEXT_PRIMARY"))
        self._action_delete.setIcon(IconManager.get_icon("trash-2", color="@COLOR_DANGER"))

    def changeEvent(self, event):
        if event.type() == QEvent.StyleChange and hasattr(self, "menu_button"):
            self._refresh_menu_icon()
            self._refresh_action_icons()
        super().changeEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit()
        super().mouseReleaseEvent(event)
