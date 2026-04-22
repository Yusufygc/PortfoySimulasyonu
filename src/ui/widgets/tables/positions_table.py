# src/ui/widgets/tables/positions_table.py
"""
PositionsTable — Pozisyon Tablosu Widget'ı

Hisse bazlı pozisyon verilerini (lot, maliyet, güncel fiyat, K/Z)
gösteren, renk kodlu QTableWidget bileşeni.

Kullanım:
    table = PositionsTable()
    table.populate(positions_data)   # list[dict] veya liste
"""
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt


class PositionsTable(QTableWidget):
    """Portföy pozisyonlarını gösteren tablo bileşeni."""

    _COLUMNS = ["Hisse", "Lot", "Ort. Maliyet", "Güncel", "Değer", "K/Z"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()

    def _setup_table(self) -> None:
        self.setColumnCount(len(self._COLUMNS))
        self.setHorizontalHeaderLabels(self._COLUMNS)

        # İlk sütun esnek, diğerleri içeriğe göre
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(self._COLUMNS)):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setProperty("cssClass", "dataTable")

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
            self._set_readonly(i, 0, pos.get("name") or "")
            self._set_readonly(i, 1, str(pos.get("quantity", "")))
            self._set_readonly(i, 2, f"₺ {pos['avg_cost']:.2f}")

            if pos.get("current_price") is not None:
                self._set_readonly(i, 3, f"₺ {pos['current_price']:.2f}")
                self._set_readonly(i, 4, f"₺ {pos['current_value']:,.2f}")

                pl = pos["profit_loss"]
                pl_item = QTableWidgetItem(f"₺ {pl:+,.2f}")
                pl_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                pl_item.setForeground(Qt.green if pl >= 0 else Qt.red)
                self.setItem(i, 5, pl_item)
            else:
                for col in (3, 4, 5):
                    self._set_readonly(i, col, "-")

    def _set_readonly(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.setItem(row, col, item)
