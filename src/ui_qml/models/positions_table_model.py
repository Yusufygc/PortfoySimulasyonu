"""
Positions Table Model — QML için optimize edilmiş portföy açık pozisyonları list/table modeli.
"""
from __future__ import annotations

from typing import List, Dict, Any
from decimal import Decimal

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    Qt,
    QByteArray,
    Signal,
    Slot,
    QTimer,
)


class PositionsTableModel(QAbstractListModel):
    # Roller
    TickerRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    QuantityRole = Qt.UserRole + 3
    AvgCostRole = Qt.UserRole + 4
    CurrentPriceRole = Qt.UserRole + 5
    DailyDiffRole = Qt.UserRole + 6
    MarketValueRole = Qt.UserRole + 7
    UnrealizedPLRole = Qt.UserRole + 8
    UnrealizedPLPctRole = Qt.UserRole + 9
    WeightRole = Qt.UserRole + 10
    IsUpRole = Qt.UserRole + 11
    FlashStateRole = Qt.UserRole + 12  # 0: None, 1: Flash Up, 2: Flash Down

    countChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._positions: List[Dict[str, Any]] = []

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            self.TickerRole: QByteArray(b"ticker"),
            self.NameRole: QByteArray(b"companyName"),
            self.QuantityRole: QByteArray(b"quantity"),
            self.AvgCostRole: QByteArray(b"avgCost"),
            self.CurrentPriceRole: QByteArray(b"currentPrice"),
            self.DailyDiffRole: QByteArray(b"dailyDiff"),
            self.MarketValueRole: QByteArray(b"marketValue"),
            self.UnrealizedPLRole: QByteArray(b"unrealizedPL"),
            self.UnrealizedPLPctRole: QByteArray(b"unrealizedPLPct"),
            self.WeightRole: QByteArray(b"weight"),
            self.IsUpRole: QByteArray(b"isUp"),
            self.FlashStateRole: QByteArray(b"flashState"),
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._positions)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._positions):
            return None

        pos = self._positions[index.row()]

        if role == self.TickerRole:
            return pos.get("ticker", "")
        elif role == self.NameRole:
            return pos.get("companyName", "")
        elif role == self.QuantityRole:
            return f"{pos.get('quantity', 0):,}"
        elif role == self.AvgCostRole:
            return f"₺{pos.get('avgCost', 0.0):,.2f}"
        elif role == self.CurrentPriceRole:
            return f"₺{pos.get('currentPrice', 0.0):,.2f}"
        elif role == self.DailyDiffRole:
            diff = pos.get("dailyDiff", 0.0)
            sign = "+" if diff >= 0 else ""
            return f"{sign}%{diff:.2f}"
        elif role == self.MarketValueRole:
            return f"₺{pos.get('marketValue', 0.0):,.2f}"
        elif role == self.UnrealizedPLRole:
            pl = pos.get("unrealizedPL", 0.0)
            sign = "+" if pl >= 0 else ""
            return f"{sign}₺{pl:,.2f}"
        elif role == self.UnrealizedPLPctRole:
            pl_pct = pos.get("unrealizedPLPct", 0.0)
            sign = "+" if pl_pct >= 0 else ""
            return f"{sign}%{pl_pct:.2f}"
        elif role == self.WeightRole:
            return f"%{pos.get('weight', 0.0):.1f}"
        elif role == self.IsUpRole:
            return pos.get("unrealizedPL", 0.0) >= 0
        elif role == self.FlashStateRole:
            return pos.get("flashState", 0)

        return None

    def set_positions(self, positions_data: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._positions = positions_data
        self.endResetModel()
        self.countChanged.emit(len(self._positions))

    def _clear_flash_states(self) -> None:
        for row, pos in enumerate(self._positions):
            if pos.get("flashState", 0) != 0:
                pos["flashState"] = 0
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [self.FlashStateRole])
