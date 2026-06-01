from __future__ import annotations
from datetime import date, timedelta
from PyQt5.QtCore import QDate, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)
from src.ui.pages.analysis.checkable_combo_box import CheckableComboBox

class ComparisonRibbonBar(QFrame):
    filter_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFramePadded")
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._init_ui()
        
    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)
        
        # Üst şerit - Kontroller
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        # Multi-Asset Selector
        controls_layout.addWidget(QLabel("Kıyaslanacak Varlıklar:"))
        self.compare_combo = CheckableComboBox("Varlık seçin")
        self.compare_combo.setMinimumWidth(220)
        self.compare_combo.selection_changed.connect(self.filter_changed.emit)
        controls_layout.addWidget(self.compare_combo)
        
        # Grafik Modu
        controls_layout.addWidget(QLabel("Grafik Modu:"))
        self.combo_mode = QComboBox()
        self.combo_mode.setProperty("cssClass", "customComboBox")
        self.combo_mode.addItems(["Normal", "Normalize (Baz 100)", "Rasyo Modu"])
        self.combo_mode.setMinimumWidth(160)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        controls_layout.addWidget(self.combo_mode)
        
        # Rasyo Seçiciler (Pay / Payda)
        self.ratio_widget = QWidget()
        ratio_layout = QHBoxLayout(self.ratio_widget)
        ratio_layout.setContentsMargins(0, 0, 0, 0)
        ratio_layout.setSpacing(6)
        
        self.combo_num = QComboBox()
        self.combo_num.setProperty("cssClass", "customComboBox")
        self.combo_num.setMinimumWidth(120)
        self.combo_num.currentIndexChanged.connect(self.filter_changed.emit)
        
        self.combo_den = QComboBox()
        self.combo_den.setProperty("cssClass", "customComboBox")
        self.combo_den.setMinimumWidth(120)
        self.combo_den.currentIndexChanged.connect(self.filter_changed.emit)
        
        ratio_layout.addWidget(QLabel("Pay:"))
        ratio_layout.addWidget(self.combo_num)
        ratio_layout.addWidget(QLabel("/"))
        ratio_layout.addWidget(QLabel("Payda:"))
        ratio_layout.addWidget(self.combo_den)
        
        self.ratio_widget.setVisible(False)
        controls_layout.addWidget(self.ratio_widget)
        
        # Tarih Seçiciler
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Tarih Aralığı:"))
        
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setProperty("cssClass", "tradeInputNormal")
        self.date_start.setMinimumHeight(36)
        self.date_start.setDate(QDate.currentDate().addMonths(-3))
        self.date_start.dateChanged.connect(self.filter_changed.emit)
        controls_layout.addWidget(self.date_start)
        
        controls_layout.addWidget(QLabel("—"))
        
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setProperty("cssClass", "tradeInputNormal")
        self.date_end.setMinimumHeight(36)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.filter_changed.emit)
        controls_layout.addWidget(self.date_end)
        
        main_layout.addLayout(controls_layout)
        
        # Alt şerit - TradingView Zaman Butonları
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.time_buttons = {}
        periods = [
            ("1A", timedelta(days=30)),
            ("3A", timedelta(days=90)),
            ("6A", timedelta(days=180)),
            ("1Y", timedelta(days=365)),
            ("YBB", None),
            ("Tümü", None),
        ]
        
        for label, delta in periods:
            btn = QPushButton(label)
            btn.setProperty("cssClass", "secondaryButton")
            btn.setMinimumHeight(28)
            btn.setMinimumWidth(50)
            btn.clicked.connect(lambda checked, l=label, d=delta: self._on_time_button_clicked(l, d))
            buttons_layout.addWidget(btn)
            self.time_buttons[label] = btn
            
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)
        
    def _on_mode_changed(self, index: int) -> None:
        # 2 is Rasyo Modu
        is_ratio = (index == 2)
        self.ratio_widget.setVisible(is_ratio)
        self.filter_changed.emit()
        
    def _on_time_button_clicked(self, label: str, delta: timedelta | None) -> None:
        today = QDate.currentDate()
        self.date_end.blockSignals(True)
        self.date_start.blockSignals(True)
        
        self.date_end.setDate(today)
        
        if label == "YBB":
            start_date = QDate(today.year(), 1, 1)
            self.date_start.setDate(start_date)
        elif label == "Tümü":
            self.date_start.setDate(today.addYears(-5))
        elif delta is not None:
            days = delta.days
            self.date_start.setDate(today.addDays(-days))
            
        self.date_end.blockSignals(False)
        self.date_start.blockSignals(False)
        
        self.filter_changed.emit()
        
    def set_assets(self, assets: list[tuple[str, str]]) -> None:
        self.compare_combo.set_items(assets)
        
        # Populate Pay/Payda combo boxes as well
        self.combo_num.blockSignals(True)
        self.combo_den.blockSignals(True)
        
        self.combo_num.clear()
        self.combo_den.clear()
        
        for name, code in assets:
            self.combo_num.addItem(name, code)
            self.combo_den.addItem(name, code)
            
        self.combo_num.blockSignals(False)
        self.combo_den.blockSignals(False)
        
    def selected_assets(self) -> list[str]:
        return self.compare_combo.selected_data()
        
    def set_selected_assets(self, codes: list[str]) -> None:
        self.compare_combo.set_selected_data(codes)
        self.filter_changed.emit()
        
    def selected_mode(self) -> str:
        return self.combo_mode.currentText()
        
    def ratio_assets(self) -> tuple[str, str]:
        return self.combo_num.currentData(), self.combo_den.currentData()
        
    def date_range(self) -> tuple[date, date]:
        start = self.date_start.date().toPyDate()
        end = self.date_end.date().toPyDate()
        return start, end
