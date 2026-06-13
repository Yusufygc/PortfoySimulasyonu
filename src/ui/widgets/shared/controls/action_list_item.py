from __future__ import annotations

import re

from src.qt_compat.qtcore import Qt, QEvent, QSize, Signal
from src.qt_compat.qtgui import QAction
from src.qt_compat.qtwidgets import QHBoxLayout, QMenu, QSizePolicy, QToolButton, QWidget

from src.ui.core.icon_manager import IconManager
from src.ui.shared.locale_tr import L10N
from src.ui.widgets.shared.controls.elided_label import ElidedLabel


class ActionListItem(QWidget):
    """List row with a trailing three-dot actions menu."""

    selected = Signal()
    edit_requested = Signal()
    delete_requested = Signal()

    def __init__(self, text: str, secondary_text: str = None, draggable: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("actionListItem")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self._draggable = draggable
        self.secondary_label = None
        self._secondary_short_text = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(6)
        self._layout = layout

        if self._draggable:
            from src.ui.widgets.shared.controls.icon_label import IconLabel
            self.drag_handle = IconLabel("grip-vertical", color="@COLOR_TEXT_MUTED", size=16)
            self.drag_handle.setFixedWidth(16)
            self.drag_handle.setCursor(Qt.OpenHandCursor)
            layout.addWidget(self.drag_handle, 0, Qt.AlignVCenter)

        self.label = ElidedLabel(text, minimum_width=18)
        self.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.label.setAutoFillBackground(False)
        self.label.setProperty("cssClass", "actionListLabel")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if secondary_text:
            secondary_candidates = self._secondary_elide_candidates(secondary_text)
            self._secondary_short_text = secondary_candidates[0] if secondary_candidates else secondary_text
            self.secondary_label = ElidedLabel(
                secondary_text,
                elide_candidates=secondary_candidates,
                minimum_width=34,
            )
            self.secondary_label.setTextInteractionFlags(Qt.NoTextInteraction)
            self.secondary_label.setProperty("cssClass", "actionListSecondaryLabel")
            self.secondary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.secondary_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            layout.addWidget(self.label, 1)
            layout.addWidget(self.secondary_label, 0, Qt.AlignVCenter)
        else:
            layout.addWidget(self.label, 1)

        self.menu_button = QToolButton()
        self.menu_button.setIconSize(QSize(20, 20))
        self.menu_button.setFixedSize(28, 28)
        self.menu_button.setCursor(Qt.PointingHandCursor)
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.menu_button.setToolTip(L10N.ISLEMLER)
        self.menu_button.setProperty("cssClass", "actionListMenuBtn")
        # Stil QSS'te: shared/lists.qss QToolButton[cssClass="actionListMenuBtn"]
        self._refresh_menu_icon()

        self._action_edit = QAction(L10N.EDIT, self)
        self._action_delete = QAction(L10N.DELETE, self)
        self._action_edit.triggered.connect(lambda checked=False: self.edit_requested.emit())
        self._action_delete.triggered.connect(lambda checked=False: self.delete_requested.emit())
        self._refresh_action_icons()

        menu = QMenu(self.menu_button)
        menu.addAction(self._action_edit)
        menu.addAction(self._action_delete)
        self.menu_button.setMenu(menu)

        layout.addWidget(self.menu_button, 0, Qt.AlignVCenter)
        self._apply_dynamic_secondary_width()

    @staticmethod
    def _secondary_elide_candidates(text: str) -> list[str]:
        match = re.fullmatch(r"\((\d+)\s+hisse\)", text or "")
        if not match:
            return []
        return [f"({match.group(1)} h.)"]

    def _available_text_width(self) -> int:
        margins = self._layout.contentsMargins()
        fixed_width = self.menu_button.width()
        if self._draggable and hasattr(self, "drag_handle"):
            fixed_width += self.drag_handle.width()
        spacing = self._layout.spacing() * max(0, self._layout.count() - 1)
        return max(0, self.width() - margins.left() - margins.right() - fixed_width - spacing)

    def _apply_dynamic_secondary_width(self) -> None:
        if self.secondary_label is None:
            return

        label_metrics = self.label.fontMetrics()
        secondary_metrics = self.secondary_label.fontMetrics()
        primary_full_width = label_metrics.horizontalAdvance(self.label.text())
        secondary_full_width = secondary_metrics.horizontalAdvance(self.secondary_label.text())
        secondary_short_width = secondary_metrics.horizontalAdvance(
            self._secondary_short_text or self.secondary_label.text()
        )

        available = self._available_text_width()
        if available >= primary_full_width + secondary_full_width:
            target_width = secondary_full_width
        else:
            target_width = secondary_short_width

        target_width = max(self.secondary_label.minimumSizeHint().width(), target_width)
        self.secondary_label.setFixedWidth(target_width)
        self.secondary_label.update()

    def _refresh_menu_icon(self):
        self.menu_button.setIcon(IconManager.get_icon("ellipsis", color="@COLOR_TEXT_PRIMARY", size=QSize(20, 20)))

    def _refresh_action_icons(self):
        self._action_edit.setIcon(IconManager.get_icon("pencil", color="@COLOR_TEXT_PRIMARY"))
        self._action_delete.setIcon(IconManager.get_icon("trash-2", color="@COLOR_DANGER"))

    def changeEvent(self, event):
        if event.type() == QEvent.StyleChange and hasattr(self, "menu_button"):
            self._refresh_menu_icon()
            self._refresh_action_icons()
            self._apply_dynamic_secondary_width()
        super().changeEvent(event)

    def resizeEvent(self, event):
        self._apply_dynamic_secondary_width()
        super().resizeEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit()
        super().mouseReleaseEvent(event)
