from decimal import Decimal
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from src.ui.formatters import display_ticker
from src.ui.shared.locale_tr import L10N
from src.ui.widgets.shared.wrapped_header_view import WrappedHeaderView


class PositionsTable(QTableWidget):
    """Model portfoy pozisyonlarini dashboard kolon duzeniyle gosteren tablo."""

    MIN_SECTION_WIDTH = 95
    POSITIVE_COLOR = QColor("#22c55e")
    NEGATIVE_COLOR = QColor("#ef4444")
    MUTED_COLOR = QColor("#666666")

    row_double_clicked = pyqtSignal(dict)
    _COLUMNS = [
        L10N.HISSE_BASLIK,
        L10N.MALIYET_FIYATI,
        L10N.GUNCEL_FIYAT,
        L10N.GUNLUK_DEGISIM_YUZDESI,
        L10N.LOT_SAYISI,
        L10N.PIYASA_DEGERI,
        L10N.TOPLAM_DEGISIM_YUZDESI,
        L10N.KAR_ZARAR_MIKTARI,
    ]
    _DETAIL_TOOLTIP = L10N.HISSE_DETAYLARINI_GORMEK_ICIN_CIFT

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()

    def _setup_table(self) -> None:
        self.setColumnCount(len(self._COLUMNS))
        self.setHorizontalHeader(WrappedHeaderView(Qt.Horizontal, self))
        self.setHorizontalHeaderLabels(self._COLUMNS)

        header = self.horizontalHeader()
        header.setMinimumSectionSize(self.MIN_SECTION_WIDTH)
        header.setStretchLastSection(False)
        for col in range(len(self._COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.Stretch)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(38)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setShowGrid(False)
        self.setWordWrap(False)
        header.setHighlightSections(False)
        self.setProperty("cssClass", "modelPositionsTable")
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def populate(self, positions: list, previous_close_map: dict[int, Decimal] | None = None) -> None:
        """Pozisyon verilerini dashboard ile ayni kolon ve hesap duzeniyle yazar."""
        self.setRowCount(0)
        previous_close_map = previous_close_map or {}

        for row, pos in enumerate(positions):
            self.insertRow(row)
            payload = {
                "stock_id": pos.get("stock_id"),
                "ticker": pos.get("ticker"),
                "name": pos.get("name"),
            }

            stock_id = pos.get("stock_id")
            quantity = self._to_decimal(pos.get("quantity"), Decimal("0"))
            avg_cost = self._to_decimal(pos.get("avg_cost"))
            total_cost = self._to_decimal(pos.get("total_cost"))
            current_price = self._to_decimal(pos.get("current_price"))
            current_value = self._current_value(quantity, current_price)
            profit_loss = self._profit_loss(current_value, total_cost, avg_cost, quantity)
            daily_change = self._change_pct(current_price, previous_close_map.get(stock_id))
            total_change = self._change_pct(current_price, avg_cost)

            values = [
                display_ticker(pos.get("ticker") or pos.get("name") or ""),
                self._format_decimal(avg_cost),
                self._format_decimal(current_price),
                self._format_pct(daily_change),
                f"{int(quantity):,}" if quantity == quantity.to_integral_value() else f"{quantity:,}",
                self._format_decimal(current_value),
                self._format_pct(total_change),
                self._format_signed_decimal(profit_loss),
            ]

            for col, text in enumerate(values):
                color = self._foreground_for(col, text, daily_change, total_change, profit_loss)
                self._set_readonly(row, col, text, payload, color=color)

    def _set_readonly(
        self,
        row: int,
        col: int,
        text: str,
        payload: dict | None = None,
        color: QColor | None = None,
    ) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignCenter)
        item.setToolTip(self._DETAIL_TOOLTIP)
        if text == "-":
            font = QFont()
            font.setItalic(True)
            item.setFont(font)
        if color is not None:
            item.setForeground(color)
        if payload is not None:
            item.setData(Qt.UserRole, payload)
        self.setItem(row, col, item)

    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        item = self.item(row, column)
        payload = item.data(Qt.UserRole) if item is not None else None
        if payload:
            self.row_double_clicked.emit(payload)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API
        self._update_hover_cursor(event.pos())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt API
        self.viewport().unsetCursor()
        super().leaveEvent(event)

    def _update_hover_cursor(self, pos) -> bool:
        has_item = self.itemAt(pos) is not None
        if has_item:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().unsetCursor()
        return has_item

    @classmethod
    def _foreground_for(
        cls,
        col: int,
        text: str,
        daily_change: Decimal | None,
        total_change: Decimal | None,
        profit_loss: Decimal | None,
    ) -> QColor | None:
        if text == "-":
            return cls.MUTED_COLOR
        if col == 3:
            return cls._signed_color(daily_change)
        if col == 6:
            return cls._signed_color(total_change)
        if col == 7:
            return cls._signed_color(profit_loss)
        return None

    @classmethod
    def _signed_color(cls, value: Decimal | None) -> QColor | None:
        if value is None:
            return None
        if value > 0:
            return cls.POSITIVE_COLOR
        if value < 0:
            return cls.NEGATIVE_COLOR
        return None

    @staticmethod
    def _to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _current_value(quantity: Decimal, current_price: Decimal | None) -> Decimal | None:
        if current_price is None:
            return None
        return current_price * quantity

    @staticmethod
    def _profit_loss(
        current_value: Decimal | None,
        total_cost: Decimal | None,
        avg_cost: Decimal | None,
        quantity: Decimal,
    ) -> Decimal | None:
        if current_value is None:
            return None
        cost = total_cost if total_cost is not None else (avg_cost * quantity if avg_cost is not None else None)
        if cost is None:
            return None
        return current_value - cost

    @staticmethod
    def _change_pct(current_price: Decimal | None, baseline: Decimal | None) -> Decimal | None:
        if current_price is None or baseline is None or baseline <= 0:
            return None
        return ((current_price - baseline) / baseline) * 100

    @staticmethod
    def _format_decimal(value: Decimal | None) -> str:
        return f"{value:,.2f}" if value is not None else "-"

    @staticmethod
    def _format_signed_decimal(value: Decimal | None) -> str:
        return f"{value:+,.2f}" if value is not None else "-"

    @staticmethod
    def _format_pct(value: Decimal | None) -> str:
        return f"%{value:+.2f}" if value is not None else "-"
