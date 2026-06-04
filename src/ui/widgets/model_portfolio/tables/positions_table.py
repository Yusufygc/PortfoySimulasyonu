from src.ui.shared.locale_tr import L10N
# src/ui/widgets/model_portfolio/tables/positions_table.py
"""
PositionsTable — Pozisyon Tablosu Widget'ı

Hisse bazlı pozisyon verilerini (lot, maliyet, güncel fiyat, K/Z)
gösteren, renk kodlu QTableWidget bileşeni.

Kullanım:
    table = PositionsTable()
    table.populate(positions_data)   # list[dict] veya liste
"""
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal
from src.ui.formatters import display_ticker


class PositionsTable(QTableWidget):
    """Portföy pozisyonlarını gösteren tablo bileşeni."""

    row_double_clicked = pyqtSignal(dict)
    _COLUMNS = ["Hisse", "Lot", L10N.ORT_MALIYET, "Güncel", "Değer", "K/Z"]
    _DETAIL_TOOLTIP = L10N.HISSE_DETAYLARINI_GORMEK_ICIN_CIFT

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()

    def _setup_table(self) -> None:
        self.setColumnCount(len(self._COLUMNS))
        self.setHorizontalHeaderLabels(self._COLUMNS)

        self.horizontalHeader().setMinimumSectionSize(92)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, len(self._COLUMNS)):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        self.setSelectionMode(QTableWidget.NoSelection)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(38)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.horizontalHeader().setHighlightSections(False)
        self.setProperty("cssClass", "modelPositionsTable")
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def populate(self, positions: list) -> None:
        """
        Pozisyon verilerini tabloya yazar.

        Args:
            positions: dict listesi. Beklenen anahtarlar:
                       name, quantity, avg_cost, current_price (None olabilir),
                       current_value, profit_loss
        """
        self.setRowCount(0)

        for i, pos in enumerate(positions):
            self.insertRow(i)
            payload = {
                "stock_id": pos.get("stock_id"),
                "ticker": pos.get("ticker"),
                "name": pos.get("name"),
            }
            self._set_readonly(i, 0, display_ticker(pos.get("name") or pos.get("ticker") or ""), payload)
            self._set_readonly(i, 1, str(pos.get("quantity", "")), payload)
            self._set_readonly(i, 2, f"₺ {pos['avg_cost']:.2f}", payload)

            if pos.get("current_price") is not None:
                self._set_readonly(i, 3, f"₺ {pos['current_price']:.2f}", payload)
                self._set_readonly(i, 4, f"₺ {pos['current_value']:,.2f}", payload)

                pl = round(pos["profit_loss"], 2)
                if pl == 0:
                    pl_item = QTableWidgetItem("₺ 0.00")
                else:
                    pl_item = QTableWidgetItem(f"₺ {pl:+,.2f}")
                    pl_item.setForeground(Qt.green if pl > 0 else Qt.red)
                
                pl_item.setFlags(Qt.ItemIsEnabled)
                pl_item.setTextAlignment(Qt.AlignCenter)
                pl_item.setData(Qt.UserRole, payload)
                pl_item.setToolTip(self._DETAIL_TOOLTIP)
                self.setItem(i, 5, pl_item)
            else:
                for col in (3, 4, 5):
                    self._set_readonly(i, col, "-", payload)

    def _set_readonly(self, row: int, col: int, text: str, payload: dict | None = None) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignCenter)
        item.setToolTip(self._DETAIL_TOOLTIP)
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
