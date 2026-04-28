# src/ui/pages/dashboard/dashboard_portfolio_table.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt5.QtGui import QColor
from decimal import Decimal

from src.ui.widgets.dashboard import PortfolioRowDelegate

class DashboardPortfolioTable(QWidget):
    """Portföy tablosu ve altındaki toplam özet satırını yöneten bileşen."""
    
    # row_double_clicked(index)
    row_double_clicked = pyqtSignal(QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(40)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setShowGrid(False)
        self.table_view.doubleClicked.connect(self.row_double_clicked.emit)
        
        self.row_delegate = PortfolioRowDelegate(self.table_view)
        self.table_view.setItemDelegate(self.row_delegate)

        layout.addWidget(self.table_view)

        # TOPLAM Özet Satırı
        self.table_summary = QTableWidget(1, 7)
        self.table_summary.horizontalHeader().setVisible(False)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_summary.setFixedHeight(40)
        self.table_summary.setSelectionMode(QTableView.NoSelection)
        self.table_summary.setFocusPolicy(Qt.NoFocus)
        self.table_summary.setEditTriggers(QTableView.NoEditTriggers)
        self.table_summary.setShowGrid(False)
        self.table_summary.setProperty("cssClass", "tableSummary")
        layout.addWidget(self.table_summary)

    def set_model(self, model):
        self.model = model
        self.table_view.setModel(self.model)

    def update_summary_row(self, total_value: Decimal, profit_loss: Decimal):
        """Alt kısımdaki toplam özet satırını günceller."""
        for col in range(7):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.table_summary.setItem(0, col, item)
            
        item_title = QTableWidgetItem("TOPLAM")
        item_title.setTextAlignment(Qt.AlignCenter)
        self.table_summary.setItem(0, 0, item_title)
        
        item_mv = QTableWidgetItem(f"{total_value:,.2f}")
        item_mv.setTextAlignment(Qt.AlignCenter)
        self.table_summary.setItem(0, 5, item_mv)
        
        item_pl = QTableWidgetItem(f"{profit_loss:+,.2f}")
        item_pl.setTextAlignment(Qt.AlignCenter)
        
        if profit_loss > 0:
            item_pl.setForeground(QColor("#22c55e"))
        elif profit_loss < 0:
            item_pl.setForeground(QColor("#ef4444"))
        else:
            item_pl.setForeground(QColor("#f1f5f9"))
            
        self.table_summary.setItem(0, 6, item_pl)
