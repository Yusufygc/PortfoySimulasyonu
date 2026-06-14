# src/ui/portfolio_table_model.py

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional
from src.qt_compat.qtgui import QColor, QFont
from src.qt_compat.qtcore import QAbstractTableModel, Qt, QModelIndex
from decimal import Decimal

from src.domain.models.position import Position
from src.ui.formatters import display_ticker
from src.ui.shared.locale_tr import L10N


class PortfolioTableData(NamedTuple):
    positions: List[Position]
    price_map: Dict[int, Decimal]
    ticker_map: Dict[int, str]
    previous_close_map: Optional[Dict[int, Decimal]] = None
    event_bus: object = None


def _fmt_price(v) -> str:
    return f"{v:,.2f}" if v is not None else "-"


def _fmt_pct(v) -> str:
    return f"%{v:+.2f}" if v is not None else "-"


def _color_for_signed_value(value) -> "QColor | None":
    if value > 0:
        return QColor("#22c55e")
    if value < 0:
        return QColor("#ef4444")
    return None


def _color_for_bg(value) -> "QColor | None":
    if value is None:
        return None
    if value > 0:
        return QColor(16, 185, 129, 20)
    if value < 0:
        return QColor(239, 68, 68, 20)
    return None


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

    def __init__(self, data: PortfolioTableData, parent=None):
        super().__init__(parent)
        self._positions = data.positions
        self._price_map = data.price_map
        self._ticker_map = data.ticker_map
        self._previous_close_map = data.previous_close_map or {}
        self._event_bus = data.event_bus

        self._headers = [
            L10N.HISSE_BASLIK,
            L10N.MALIYET_FIYATI,
            L10N.GUNCEL_FIYAT,
            L10N.GUNLUK_DEGISIM_YUZDESI,
            L10N.LOT_SAYISI,
            L10N.PIYASA_DEGERI,
            L10N.TOPLAM_DEGISIM_YUZDESI,
            L10N.KAR_ZARAR_MIKTARI,
        ]

        if self._event_bus:
            self._event_bus.prices_updated.connect(self._on_prices_updated)

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._positions)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return section + 1

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        position = self._positions[index.row()]
        stock_id = position.stock_id
        current_price = self._price_map.get(stock_id)
        col = index.column()

        display_text = self._get_display_text(position, col, current_price)

        if role == Qt.DisplayRole:
            return display_text

        if role == Qt.ForegroundRole:
            return self._get_foreground_color(position, col, current_price, display_text)

        if role == Qt.BackgroundRole:
            return self._get_background_color(position, col, current_price)

        if role == Qt.FontRole:
            return self._get_font(display_text)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
            
        if role == Qt.ToolTipRole:
            return "Hisse detaylarını görmek için çift tıkla"

        return None

    def _display_col_ticker(self, stock_id: int) -> str:
        ticker = self._ticker_map.get(stock_id)
        return display_ticker(ticker) if ticker is not None else str(stock_id)

    def _display_col_market_value(self, position: Position, current_price: Decimal | None) -> str:
        if current_price is None:
            return "-"
        return f"{position.market_value(current_price):,.2f}"

    def _display_col_pl(self, position: Position, current_price: Decimal | None) -> str:
        if current_price is None:
            return "-"
        return f"{position.unrealized_pl(current_price):+,.2f}"

    def _get_display_text(self, position: Position, col: int, current_price: Decimal | None) -> str:
        stock_id = position.stock_id
        if col == 0:
            return self._display_col_ticker(stock_id)
        if col == 1:
            return _fmt_price(position.average_cost)
        if col == 2:
            return _fmt_price(current_price)
        if col == 3:
            return _fmt_pct(self._daily_change_pct(stock_id, current_price))
        if col == 4:
            return f"{position.total_quantity:,}"
        if col == 5:
            return self._display_col_market_value(position, current_price)
        if col == 6:
            return _fmt_pct(self._total_change_pct(position, current_price))
        if col == 7:
            return self._display_col_pl(position, current_price)
        return ""

    def _get_foreground_color(self, position: Position, col: int, current_price: Decimal | None, display_text: str):
        if display_text == "-":
            return QColor("#666666")
        if current_price is None:
            return None
        if col == 7:
            return _color_for_signed_value(position.unrealized_pl(current_price))
        if col == 3:
            change_pct = self._daily_change_pct(position.stock_id, current_price)
            if change_pct is not None:
                return _color_for_signed_value(change_pct)
        if col == 6:
            change_pct = self._total_change_pct(position, current_price)
            if change_pct is not None:
                return _color_for_signed_value(change_pct)
        return None

    def _get_background_color(self, position: Position, col: int, current_price: Decimal | None):
        if current_price is None:
            return None
        if col == 7:
            return _color_for_bg(position.unrealized_pl(current_price))
        if col == 3:
            return _color_for_bg(self._daily_change_pct(position.stock_id, current_price))
        if col == 6:
            return _color_for_bg(self._total_change_pct(position, current_price))
        return None

    def _get_font(self, display_text: str):
        if display_text == "-":
            font = QFont()
            font.setItalic(True)
            return font
        return None

    # UI'yı güncellemek için helper
    def update_data(
        self,
        positions: List[Position],
        price_map: Dict[int, Decimal],
        ticker_map: Dict[int, str],
        previous_close_map: Dict[int, Decimal],
    ):
        self.beginResetModel()
        self._positions = positions
        self._price_map = price_map
        self._ticker_map = ticker_map
        self._previous_close_map = previous_close_map
        self.endResetModel()

    def get_position(self, row: int) -> Position:
        """
        Verilen satırdaki Position objesini döner.
        """
        if row < 0 or row >= len(self._positions):
            raise IndexError("Row out of range in PortfolioTableModel.get_position")
        return self._positions[row]

    def _on_prices_updated(self, new_prices: Dict[int, Decimal]):
        """EventBus'tan gelen anlık fiyat güncellemesi. Sadece değişen hücreleri/satırları render eder."""
        if not new_prices:
            return

        self._price_map.update(new_prices)

        changed_rows = []
        for row, pos in enumerate(self._positions):
            if pos.stock_id in new_prices:
                changed_rows.append(row)

        for row in changed_rows:
            top_left = self.index(row, 2)  # 2: Güncel Fiyat kolonu
            bottom_right = self.index(row, 7)  # 7: Kar/Zarar kolonu
            self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole, Qt.ForegroundRole, Qt.BackgroundRole])

    def _daily_change_pct(self, stock_id: int, current_price: Decimal | None) -> Decimal | None:
        if current_price is None:
            return None
        previous_close = self._previous_close_map.get(stock_id)
        if previous_close is None or previous_close <= 0:
            return None
        return ((current_price - previous_close) / previous_close) * 100

    @staticmethod
    def _total_change_pct(position: Position, current_price: Decimal | None) -> Decimal | None:
        if current_price is None:
            return None
        avg = position.average_cost
        if avg is None or avg <= 0:
            return None
        return ((current_price - avg) / avg) * 100


