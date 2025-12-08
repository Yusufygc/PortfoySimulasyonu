# src/ui/portfolio_table_model.py

from __future__ import annotations

from typing import List, Dict

from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex, QVariant
from decimal import Decimal

from src.domain.models.position import Position


class PortfolioTableModel(QAbstractTableModel):
    """
    Basit portföy tablo modeli.

    Şimdilik kolonlar:
      0: Hisse ID (stock_id)
      1: Lot (total_quantity)
      2: Ortalama Maliyet
      3: Güncel Fiyat
      4: Piyasa Değeri
      5: Gerçekleşmemiş Kar/Zarar
    """

    def __init__(
        self,
        positions: List[Position],
        price_map: Dict[int, Decimal],
        ticker_map: Dict[int, str],
        parent=None,
    ):
        super().__init__(parent)
        self._positions = positions
        self._price_map = price_map
        self._ticker_map = ticker_map  # { stock_id: "ASELS.IS" ... }
        self._headers = [
            "Hisse",          # <-- Stock ID yerine
            "Lot",
            "Ort. Maliyet",
            "Güncel Fiyat",
            "Piyasa Değeri",
            "Gerç. Olmayan K/Z",
        ]

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._positions)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return section + 1

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.TextAlignmentRole):
            return QVariant()

        position = self._positions[index.row()]
        stock_id = position.stock_id
        current_price = self._price_map.get(stock_id)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        col = index.column()
        if col == 0:
            ticker = self._ticker_map.get(stock_id)
            return ticker if ticker is not None else str(stock_id)
        elif col == 1:
            return str(position.total_quantity)
        elif col == 2:
            avg = position.average_cost
            return f"{avg:.2f}" if avg is not None else "-"
        elif col == 3:
            return f"{current_price:.2f}" if current_price is not None else "-"
        elif col == 4:
            if current_price is None:
                return "-"
            mv = position.market_value(current_price)
            return f"{mv:.2f}"
        elif col == 5:
            if current_price is None:
                return "-"
            u_pl = position.unrealized_pl(current_price)
            return f"{u_pl:.2f}"

        return QVariant()

    # UI'yı güncellemek için helper
    def update_data(
        self,
        positions: List[Position],
        price_map: Dict[int, Decimal],
        ticker_map: Dict[int, str],
    ):
        self.beginResetModel()
        self._positions = positions
        self._price_map = price_map
        self._ticker_map = ticker_map
        self.endResetModel()

    

    def get_position(self, row: int) -> Position:
        """
        Verilen satırdaki Position objesini döner.
        """
        if row < 0 or row >= len(self._positions):
            raise IndexError("Row out of range in PortfolioTableModel.get_position")
        return self._positions[row]

