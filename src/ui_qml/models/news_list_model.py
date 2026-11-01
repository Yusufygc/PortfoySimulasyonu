"""Haber paneli için sözlük tabanlı liste modeli (rol adları satır sözlüğü anahtarlarıdır)."""
from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

ROLE_KEYS = ("title", "summary", "sourceName", "sourceId", "timeText", "url", "symbols", "language", "badge")


class NewsListModel(QAbstractListModel):
    countChanged = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: List[Dict[str, Any]] = []

    def roleNames(self) -> Dict[int, QByteArray]:
        return {Qt.UserRole + 1 + i: QByteArray(key.encode()) for i, key in enumerate(ROLE_KEYS)}

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        position = role - Qt.UserRole - 1
        if 0 <= position < len(ROLE_KEYS):
            return self._rows[index.row()].get(ROLE_KEYS[position])
        return None

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()
        self.countChanged.emit(len(self._rows))

    def row_at(self, index: int) -> Dict[str, Any]:
        return self._rows[index] if 0 <= index < len(self._rows) else {}
