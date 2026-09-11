"""
ListTableModel — QML `TableView`/`ListView` için genel amaçlı taban model
(bkz. plan §7.1 "models/" katmanı, d1 Controller/Model Temel Katman).

Planlanan 5 tablo modelinin (portfolio/trade_history/screener/financial/watchlist)
ortak boilerplate'ini (rowCount/columnCount/data/headerData) tek yerde toplar —
her concrete kullanım yalnızca bir `ColumnSpec` listesi tanımlar, satır tipi
(dict, dataclass, domain modeli) `accessor` fonksiyonuna bağlı olduğundan serbesttir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Sequence

from src.qt_compat.qtcore import QAbstractTableModel, QModelIndex, Qt


@dataclass(frozen=True)
class ColumnSpec:
    """Bir tablo sütununun başlığı ve satırdan görüntülenecek değeri çıkaran fonksiyonu."""
    header: str
    accessor: Callable[[Any], Any]


class ListTableModel(QAbstractTableModel):
    """Sabit `ColumnSpec` listesi + `set_rows()` ile değiştirilebilen satır listesiyle çalışır."""

    def __init__(self, columns: Sequence[ColumnSpec], rows: Sequence[Any] = (), parent=None) -> None:
        super().__init__(parent)
        self._columns: List[ColumnSpec] = list(columns)
        self._rows: List[Any] = list(rows)

    def set_rows(self, rows: Sequence[Any]) -> None:
        """Satır listesini tamamen değiştirir (QML tarafına `beginResetModel`/`endResetModel` ile bildirilir)."""
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_at(self, row_index: int) -> Any:
        return self._rows[row_index]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        if not (0 <= index.row() < len(self._rows)) or not (0 <= index.column() < len(self._columns)):
            return None
        row = self._rows[index.row()]
        column = self._columns[index.column()]
        return column.accessor(row)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if not (0 <= section < len(self._columns)):
            return None
        return self._columns[section].header
