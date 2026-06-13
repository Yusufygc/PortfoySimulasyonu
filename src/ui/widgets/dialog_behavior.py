from __future__ import annotations

from typing import Callable

from src.qt_compat.qtcore import QObject, Qt, QEvent
from src.qt_compat.qtwidgets import (
    QAbstractButton,
    QComboBox,
    QDateEdit,
    QDialog,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)


class _DialogEnterFilter(QObject):
    def __init__(self, dialog: QDialog, primary_button: QAbstractButton | None, enter_handler: Callable[[], None] | None):
        super().__init__(dialog)
        self._dialog = dialog
        self._primary_button = primary_button
        self._enter_handler = enter_handler

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if event.type() != QEvent.KeyPress:
            return False
        if event.key() not in (Qt.Key_Return, Qt.Key_Enter):
            return False
        if event.modifiers() not in (Qt.NoModifier, Qt.KeypadModifier):
            return False
        if self._should_ignore_focus_widget():
            return False

        if self._enter_handler is not None:
            self._enter_handler()
            return True
        if self._primary_button is not None and self._primary_button.isEnabled() and self._primary_button.isVisible():
            self._primary_button.click()
            return True
        return False

    def _should_ignore_focus_widget(self) -> bool:
        widget = self._dialog.focusWidget()
        if isinstance(widget, (QTextEdit, QPlainTextEdit)):
            return True
        if isinstance(widget, QComboBox) and widget.view().isVisible():
            return True
        if isinstance(widget, QDateEdit):
            calendar = widget.calendarWidget()
            return bool(calendar and calendar.isVisible())
        for combo in self._dialog.findChildren(QComboBox):
            if combo.view().isVisible():
                return True
        for date_edit in self._dialog.findChildren(QDateEdit):
            calendar = date_edit.calendarWidget()
            if calendar and calendar.isVisible():
                return True
        return False


def configure_dialog_behavior(
    dialog: QDialog,
    primary_button: QAbstractButton | None = None,
    enter_handler: Callable[[], None] | None = None,
) -> None:
    dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    dialog.setWindowFlag(Qt.WindowCloseButtonHint, True)

    if primary_button is not None:
        if hasattr(primary_button, "setDefault"):
            primary_button.setDefault(True)
        if hasattr(primary_button, "setAutoDefault"):
            primary_button.setAutoDefault(True)

    event_filter = _DialogEnterFilter(dialog, primary_button, enter_handler)
    dialog.installEventFilter(event_filter)
    for child in dialog.findChildren(QWidget):
        child.installEventFilter(event_filter)

    filters = getattr(dialog, "_dialog_behavior_filters", [])
    filters.append(event_filter)
    dialog._dialog_behavior_filters = filters
