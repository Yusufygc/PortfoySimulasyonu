# src/ui/pages/analysis/analysis_filter_panel.py

from datetime import date, timedelta
from typing import Dict, List, Tuple, Callable

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QAbstractItemView,
    QComboBox, QDateEdit, QPushButton
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal

class AnalysisFilterPanel(QFrame):
    """Analiz sayfasının sol panelindeki denetimleri içerir."""
    
    # Herhangi bir filtre değiştiğinde tetiklenir
    filter_changed = pyqtSignal()
    save_requested = pyqtSignal()
    
    CHART_PRICE = "Fiyat Grafiği"
    CHART_RETURNS = "Getiri Grafiği (%)"
    CHART_COMPARISON = "Normalize Karşılaştırma"
    CHART_PORTFOLIO_COST = "Portföy Dağılımı (Maliyet)"
    CHART_PORTFOLIO_VALUE = "Portföy Dağılımı (Güncel Değer)"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.earliest_date_calculator: Callable[[], date] = lambda: date.today() - timedelta(days=30)
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("analysisLeftPanel")
        self.setFixedWidth(250)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        lbl_stocks = QLabel("Hisse Seç")
        lbl_stocks.setProperty("cssClass", "panelSubtitle")
        layout.addWidget(lbl_stocks)

        self.stock_list = QListWidget()
        self.stock_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.stock_list.setAlternatingRowColors(True)
        self.stock_list.setMaximumHeight(200)
        self.stock_list.itemSelectionChanged.connect(self.filter_changed.emit)
        self.stock_list.setProperty("cssClass", "stockListWidget")
        layout.addWidget(self.stock_list)

        lbl_chart_type = QLabel("Grafik Türü")
        lbl_chart_type.setProperty("cssClass", "panelSubtitle")
        layout.addWidget(lbl_chart_type)

        self.combo_chart_type = QComboBox()
        self.combo_chart_type.addItems([
            self.CHART_PRICE,
            self.CHART_RETURNS,
            self.CHART_COMPARISON,
            self.CHART_PORTFOLIO_COST,
            self.CHART_PORTFOLIO_VALUE,
        ])
        self.combo_chart_type.currentTextChanged.connect(lambda _: self.filter_changed.emit())
        self.combo_chart_type.setProperty("cssClass", "customComboBox")
        layout.addWidget(self.combo_chart_type)

        lbl_date_range = QLabel("Tarih Aralığı")
        lbl_date_range.setProperty("cssClass", "panelSubtitle")
        layout.addWidget(lbl_date_range)

        date_layout = QVBoxLayout()
        date_layout.setSpacing(5)
        
        lbl_start = QLabel("Başlangıç:")
        lbl_start.setProperty("cssClass", "dateLabel")
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.dateChanged.connect(self.filter_changed.emit)
        self.date_start.setProperty("cssClass", "tradeInputNormal")
        date_layout.addWidget(lbl_start)
        date_layout.addWidget(self.date_start)
        
        lbl_end = QLabel("Bitiş:")
        lbl_end.setProperty("cssClass", "dateLabel")
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.filter_changed.emit)
        self.date_end.setProperty("cssClass", "tradeInputNormal")
        date_layout.addWidget(lbl_end)
        date_layout.addWidget(self.date_end)
        
        layout.addLayout(date_layout)

        quick_date_layout = QHBoxLayout()
        quick_date_layout.setSpacing(5)
        
        btn_1w = QPushButton("1H")
        btn_1w.setProperty("cssClass", "quickDateBtn")
        btn_1w.clicked.connect(lambda: self._set_quick_date(7))
        
        btn_1m = QPushButton("1A")
        btn_1m.setProperty("cssClass", "quickDateBtn")
        btn_1m.clicked.connect(lambda: self._set_quick_date(30))
        
        btn_3m = QPushButton("3A")
        btn_3m.setProperty("cssClass", "quickDateBtn")
        btn_3m.clicked.connect(lambda: self._set_quick_date(90))
        
        btn_1y = QPushButton("1Y")
        btn_1y.setProperty("cssClass", "quickDateBtn")
        btn_1y.clicked.connect(lambda: self._set_quick_date(365))
        
        btn_all = QPushButton("Tümü")
        btn_all.setProperty("cssClass", "quickDateBtn")
        btn_all.clicked.connect(self._set_all_time)
        
        quick_date_layout.addWidget(btn_1w)
        quick_date_layout.addWidget(btn_1m)
        quick_date_layout.addWidget(btn_3m)
        quick_date_layout.addWidget(btn_1y)
        quick_date_layout.addWidget(btn_all)
        layout.addLayout(quick_date_layout)

        layout.addStretch()

        self.btn_save = QPushButton("💾 Grafiği Kaydet")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_requested.emit)
        self.btn_save.setProperty("cssClass", "primaryButtonLarge")
        layout.addWidget(self.btn_save)

    def set_stocks(self, stock_map: Dict[int, str]):
        self.stock_list.blockSignals(True)
        self.stock_list.clear()
        for stock_id, ticker in stock_map.items():
            item = QListWidgetItem(ticker)
            item.setData(Qt.UserRole, stock_id)
            self.stock_list.addItem(item)
        self.stock_list.blockSignals(False)

    def get_selected_tickers(self) -> List[str]:
        return [item.text() for item in self.stock_list.selectedItems()]

    def get_selected_stock_ids(self) -> List[int]:
        return [item.data(Qt.UserRole) for item in self.stock_list.selectedItems()]

    def get_chart_type(self) -> str:
        return self.combo_chart_type.currentText()

    def get_date_range(self) -> Tuple[date, date]:
        return self.date_start.date().toPyDate(), self.date_end.date().toPyDate()

    def set_earliest_date_calculator(self, func: Callable[[], date]):
        self.earliest_date_calculator = func

    def _set_quick_date(self, days: int):
        end_date = QDate.currentDate()
        earliest = self.earliest_date_calculator()
        calculated_start = date.today() - timedelta(days=days)
        
        if calculated_start < earliest:
            start_date = QDate(earliest.year, earliest.month, earliest.day)
        else:
            start_date = end_date.addDays(-days)
        
        self.date_start.blockSignals(True)
        self.date_end.blockSignals(True)
        self.date_start.setDate(start_date)
        self.date_end.setDate(end_date)
        self.date_start.blockSignals(False)
        self.date_end.blockSignals(False)
        self.filter_changed.emit()

    def _set_all_time(self):
        earliest = self.earliest_date_calculator()
        start_date = QDate(earliest.year, earliest.month, earliest.day)
        end_date = QDate.currentDate()
        
        self.date_start.blockSignals(True)
        self.date_end.blockSignals(True)
        self.date_start.setDate(start_date)
        self.date_end.setDate(end_date)
        self.date_start.blockSignals(False)
        self.date_end.blockSignals(False)
        self.filter_changed.emit()
