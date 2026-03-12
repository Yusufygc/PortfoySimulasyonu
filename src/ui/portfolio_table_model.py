# src/ui/portfolio_table_model.py

from __future__ import annotations

from typing import List, Dict
from PyQt5.QtGui import QColor, QFont
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
            "Hisse",
            "Güncel Fiyat",
            "Değişim %",
            "Lot",
            "Ort. Maliyet",
            "Piyasa Değeri",
            "Kar/Zarar",
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
        if not index.isValid():
            return QVariant()

        position = self._positions[index.row()]
        stock_id = position.stock_id
        current_price = self._price_map.get(stock_id)

        # Görüntülenecek metni belirleyelim, böylece Foreground ve Font rollerinde kullanabiliriz.
        display_text = ""
        col = index.column()
        if col == 0: # HISSE
            ticker = self._ticker_map.get(stock_id)
            display_text = ticker if ticker is not None else str(stock_id)
        elif col == 1: # GÜNCEL FİYAT
            display_text = f"{current_price:,.2f}" if current_price is not None else "-"
        elif col == 2: # DEĞİŞİM%
            if current_price is None: 
                display_text = "-"
            else:
                avg = position.average_cost
                if avg and avg > 0:
                    pct = ((current_price - avg) / avg) * 100
                    display_text = f"%{pct:+.2f}"
                else:
                    display_text = "-"
        elif col == 3: # LOT
            display_text = f"{position.total_quantity:,}"
        elif col == 4: # ORT. MALİYET
            avg = position.average_cost
            display_text = f"{avg:,.2f}" if avg is not None else "-"
        elif col == 5: # PİYASA DEĞERİ
            if current_price is None: 
                display_text = "-"
            else:
                mv = position.market_value(current_price)
                display_text = f"{mv:,.2f}"
        elif col == 6: # KAR/ZARAR
            if current_price is None: 
                display_text = "-"
            else:
                u_pl = position.unrealized_pl(current_price)
                display_text = f"{u_pl:+,.2f}"


        if role == Qt.ForegroundRole:
            if display_text == "-":
                return QColor("#666666")
                
            if current_price is not None:
                # 6. Kolon: Gerç. Olmayan K/Z
                if col == 6:
                    pl = position.unrealized_pl(current_price)
                    if pl > 0:
                        return QColor("#22c55e")  # Yeşil
                    elif pl < 0:
                        return QColor("#ef4444")  # Kırmızı
                
                # 2. Kolon: Değişim %
                elif col == 2:
                    avg = position.average_cost
                    if avg and avg > 0:
                        change_pct = ((current_price - avg) / avg) * 100
                        if change_pct > 0:
                            return QColor("#22c55e")
                        elif change_pct < 0:
                            return QColor("#ef4444")
                            
            return QVariant()

        if role == Qt.FontRole:
            if display_text == "-":
                font = QFont()
                font.setItalic(True)
                return font
            return QVariant()

        if role == Qt.DisplayRole:
            return display_text

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
            
        if role == Qt.ToolTipRole:
            return "Hisse detaylarını görmek için çift tıkla"

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

