# src/ui/widgets/tables/suggestions_table.py
"""
SuggestionsTable — Optimizasyon Öneri Tablosu Widget'ı

Hisse bazlı Mevcut % / Optimal % / Fark / Öneri sütunlarını
içeren, renk kodlu optimizasyon öneri tablosu.

Kullanım:
    table = SuggestionsTable()
    table.populate(result.suggestions)
"""
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt


class SuggestionsTable(QTableWidget):
    """Optimizasyon sonucu öneri tablosu."""

    _COLUMNS = ["Hisse", "Mevcut %", "Optimal %", "Fark", "Öneri"]

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

    def populate(self, suggestions) -> None:
        """
        Öneri listesini tabloya doldurur.

        Args:
            suggestions: OptimizationSuggestion listesi
                         (.symbol, .current_weight, .optimal_weight, .change, .action)
        """
        self.setRowCount(0)

        for i, sug in enumerate(suggestions):
            self.insertRow(i)
            self._set_readonly(i, 0, sug.symbol)
            self._set_readonly(i, 1, f"{sug.current_weight:.2f}%", Qt.AlignCenter)
            self._set_readonly(i, 2, f"{sug.optimal_weight:.2f}%", Qt.AlignCenter)

            # Fark — renk kodlu
            change_item = QTableWidgetItem(f"{sug.change:+.2f}%")
            change_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            change_item.setTextAlignment(Qt.AlignCenter)
            color = Qt.green if sug.change > 0 else Qt.red if sug.change < 0 else Qt.gray
            change_item.setForeground(color)
            self.setItem(i, 3, change_item)

            # Öneri (Aksiyon) — renk kodlu
            action_item = QTableWidgetItem(sug.action)
            action_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            action_item.setTextAlignment(Qt.AlignCenter)
            if sug.action == "EKLE":
                action_item.setForeground(Qt.green)
            elif sug.action == "AZALT":
                action_item.setForeground(Qt.red)
            else:
                action_item.setForeground(Qt.gray)
            self.setItem(i, 4, action_item)

    def _set_readonly(self, row: int, col: int, text: str, align=None) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if align is not None:
            item.setTextAlignment(align)
        self.setItem(row, col, item)
