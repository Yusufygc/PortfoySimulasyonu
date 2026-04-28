from __future__ import annotations

from PyQt5.QtCore import Qt, QSize, pyqtSignal
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
        self.label.setStyleSheet(
            "QLabel { background: transparent; border: none; color: #f8fafc; font-size: 15px; }"
        )
        layout.addWidget(self.label, 1)

        self.menu_button = QToolButton()
        self.menu_button.setIcon(IconManager.get_icon("ellipsis", color="@COLOR_TEXT_PRIMARY", size=QSize(20, 20)))
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

        menu = QMenu(self.menu_button)
        action_edit = QAction(IconManager.get_icon("pencil", color="@COLOR_TEXT_PRIMARY"), "Düzenle", self)
        action_delete = QAction(IconManager.get_icon("trash-2", color="@COLOR_DANGER"), "Sil", self)
        action_edit.triggered.connect(lambda checked=False: self.edit_requested.emit())
        action_delete.triggered.connect(lambda checked=False: self.delete_requested.emit())
        menu.addAction(action_edit)
        menu.addAction(action_delete)
        self.menu_button.setMenu(menu)

        layout.addWidget(self.menu_button, 0, Qt.AlignVCenter)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit()
        super().mouseReleaseEvent(event)
