from __future__ import annotations

from typing import List

from PyQt5.QtCore import QEvent, QPoint, Qt, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QComboBox, QFrame, QLineEdit, QListView, QVBoxLayout


class CheckableComboBox(QComboBox):
    selection_changed = pyqtSignal()

    def __init__(self, placeholder: str = "Se\u00e7im yap\u0131n", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder
        self._popup_is_open = False

        self.setProperty("cssClass", "customComboBox")
        self.setEditable(True)
        self.setMinimumHeight(42)
        self.setMaxVisibleItems(10)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setCursor(Qt.PointingHandCursor)
        self.lineEdit().setPlaceholderText(placeholder)
        self.lineEdit().installEventFilter(self)
        self.setInsertPolicy(QComboBox.NoInsert)

        model = QStandardItemModel(self)
        self.setModel(model)
        model.itemChanged.connect(self._on_item_changed)

        self._popup_frame = QFrame(None, Qt.Popup | Qt.FramelessWindowHint)
        self._popup_frame.setProperty("cssClass", "analysisComboPopup")
        self._popup_frame.installEventFilter(self)

        popup_layout = QVBoxLayout(self._popup_frame)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.setSpacing(0)

        self._popup_view = QListView(self._popup_frame)
        self._popup_view.setProperty("cssClass", "analysisComboPopupList")
        self._popup_view.setModel(model)
        self._popup_view.setUniformItemSizes(True)
        self._popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._popup_view.setSelectionMode(QListView.NoSelection)
        self._popup_view.viewport().installEventFilter(self)
        popup_layout.addWidget(self._popup_view)

        self._update_text()

    def popup_view(self) -> QListView:
        return self._popup_view

    def set_items(self, items: List[tuple[str, str]]) -> None:
        selected = set(self.selected_data())
        model: QStandardItemModel = self.model()
        model.blockSignals(True)
        model.clear()
        for label, value in items:
            item = QStandardItem(label)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setData(value, Qt.UserRole)
            item.setData(Qt.Checked if value in selected else Qt.Unchecked, Qt.CheckStateRole)
            model.appendRow(item)
        model.blockSignals(False)
        self._update_text()
        self._update_popup_geometry()

    def selected_data(self) -> List[str]:
        model: QStandardItemModel = self.model()
        values: List[str] = []
        for idx in range(model.rowCount()):
            item = model.item(idx)
            if item.checkState() == Qt.Checked:
                values.append(item.data(Qt.UserRole))
        return values

    def set_selected_data(self, values: List[str]) -> None:
        selected = set(values)
        model: QStandardItemModel = self.model()
        model.blockSignals(True)
        for idx in range(model.rowCount()):
            item = model.item(idx)
            item.setCheckState(Qt.Checked if item.data(Qt.UserRole) in selected else Qt.Unchecked)
        model.blockSignals(False)
        self._update_text()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._toggle_popup()
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, obj, event) -> bool:
        popup_view = getattr(self, "_popup_view", None)
        popup_frame = getattr(self, "_popup_frame", None)

        if obj is self.lineEdit() and event.type() == QEvent.MouseButtonRelease:
            self._toggle_popup()
            return True

        if popup_view is not None and obj is popup_view.viewport() and event.type() == QEvent.MouseButtonRelease:
            index = popup_view.indexAt(event.pos())
            if index.isValid():
                item = self.model().itemFromIndex(index)
                next_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                item.setCheckState(next_state)
            return True

        if popup_frame is not None and obj is popup_frame and event.type() == QEvent.Hide:
            self._popup_is_open = False

        return False

    def showPopup(self) -> None:
        if self._popup_is_open:
            return
        self._update_popup_geometry()
        popup_pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        self._popup_frame.move(popup_pos)
        self._popup_frame.show()
        self._popup_frame.raise_()
        self._popup_view.setFocus()
        self._popup_view.scrollToTop()
        self._popup_is_open = True

    def hidePopup(self) -> None:
        self._popup_is_open = False
        self._popup_frame.hide()

    def _toggle_popup(self) -> None:
        if self._popup_is_open:
            self.hidePopup()
        else:
            self.showPopup()

    def _on_item_changed(self, _item) -> None:
        self._update_text()
        self.selection_changed.emit()

    def _update_text(self) -> None:
        model: QStandardItemModel = self.model()
        labels = [model.item(idx).text() for idx in range(model.rowCount()) if model.item(idx).checkState() == Qt.Checked]
        if not labels:
            text = self._placeholder
        elif len(labels) == 1:
            text = labels[0]
        else:
            text = f"{len(labels)} se\u00e7im"
        line_edit: QLineEdit = self.lineEdit()
        line_edit.setText(text)
        line_edit.setCursorPosition(0)

    def _update_popup_geometry(self) -> None:
        row_count = self.model().rowCount()
        visible_rows = min(max(row_count, 1), self.maxVisibleItems())
        row_height = self._popup_view.sizeHintForRow(0) if row_count else self.height()
        row_height = max(row_height, 32)
        popup_width = max(self.width(), 300)
        popup_height = (visible_rows * row_height) + 12
        self._popup_view.setMinimumWidth(popup_width)
        self._popup_view.setMinimumHeight(popup_height)
        self._popup_frame.resize(popup_width, popup_height)
