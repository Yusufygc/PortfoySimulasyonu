from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import date, timedelta
from typing import Dict, List

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
)

from src.application.services.analysis import BenchmarkDefinition, PortfolioOption
from src.ui.formatters import display_ticker

from .benchmark_chip_group import BenchmarkChipGroup
from .checkable_combo_box import CheckableComboBox


class AnalysisControlPanel(QFrame):
    filter_changed = pyqtSignal()
    source_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")
        self.setMinimumWidth(360)
        self.setMaximumWidth(400)
        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._earliest_date = date.today() - timedelta(days=365)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Filtre ve Se\u00e7im")
        title.setProperty("cssClass", "panelTitleLarge")
        layout.addWidget(title)

        self.combo_portfolio = self._create_combo_box("Portf\u00f6y")
        self.combo_portfolio.currentIndexChanged.connect(self._on_source_changed)
        layout.addWidget(self._wrap_field("Portf\u00f6y", self.combo_portfolio))

        self.combo_currency = self._create_combo_box(L10N.PARA_BIRIMI)
        self.combo_currency.addItems(["TL", "USD", L10N.REAL_TUFE_DUZELTILMIS])
        self.combo_currency.currentIndexChanged.connect(self.filter_changed.emit)
        layout.addWidget(self._wrap_field(L10N.PARA_BIRIMI, self.combo_currency, L10N.ANALIZ_VERILERINI_HESAPLAMA_BIRIMI))

        self.stock_combo = CheckableComboBox(L10N.HISSE_SECIN)
        self.stock_combo.selection_changed.connect(self.filter_changed.emit)
        layout.addWidget(
            self._wrap_field(
                L10N.HISSE_FILTRESI,
                self.stock_combo,
                L10N.NOT_HISSE_SECILDIGINDE_PORTFOYDEKI_NAKIT,
            )
        )

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setProperty("cssClass", "analysisDateInput")
        self.date_start.setMinimumHeight(45)
        self.date_start.setMinimumWidth(125)
        self.date_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.date_start.setDate(QDate.currentDate().addMonths(-3))
        self.date_start.dateChanged.connect(self.filter_changed.emit)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setProperty("cssClass", "analysisDateInput")
        self.date_end.setMinimumHeight(45)
        self.date_end.setMinimumWidth(125)
        self.date_end.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.filter_changed.emit)

        # Başlangıç ve bitiş tarihlerini tek bir "Tarih Aralığı" kartında birleştiriyoruz
        dates_frame = QFrame()
        dates_frame.setProperty("cssClass", "analysisFilterCard")
        dates_layout = QVBoxLayout(dates_frame)
        dates_layout.setContentsMargins(15, 15, 15, 15)
        dates_layout.setSpacing(10)

        dates_title = QLabel(L10N.TARIH_ARALIGI)
        dates_title.setProperty("cssClass", "panelTitle")
        dates_layout.addWidget(dates_title)

        pickers_layout = QHBoxLayout()
        pickers_layout.setSpacing(6)
        pickers_layout.setContentsMargins(0, 0, 0, 0)
        pickers_layout.addWidget(self.date_start, 1)
        
        lbl_to = QLabel("—")
        lbl_to.setAlignment(Qt.AlignCenter)
        lbl_to.setProperty("cssClass", "dateSeparatorLabel")
        pickers_layout.addWidget(lbl_to)
        
        pickers_layout.addWidget(self.date_end, 1)
        dates_layout.addLayout(pickers_layout)
        layout.addWidget(dates_frame)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)
        for label, days in [("1A", 30), ("3A", 90), ("6A", 180), ("1Y", 365)]:
            button = QPushButton(label)
            button.setProperty("cssClass", "quickDateBtn")
            button.clicked.connect(lambda _, d=days: self._set_quick_date(d))
            quick_row.addWidget(button)

        btn_all = QPushButton(L10N.TUMU)
        btn_all.setProperty("cssClass", "quickDateBtn")
        btn_all.clicked.connect(self._set_all_time)
        quick_row.addWidget(btn_all)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        self.combo_benchmark = self._create_combo_box("Benchmark")
        self.combo_benchmark.currentIndexChanged.connect(self.filter_changed.emit)
        layout.addWidget(self._wrap_field(L10N.KIYASLAMA_ENDEKSI, self.combo_benchmark, L10N.GENEL_BAKISTA_FARK_HESABI_ICIN))
        layout.addStretch()

    def _create_combo_box(self, _placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setProperty("cssClass", "customComboBox")
        combo.setMinimumHeight(38)
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        return combo

    def _wrap_field(self, title: str, widget, description: str | None = None) -> QFrame:
        frame = QFrame()
        frame.setProperty("cssClass", "analysisFilterCard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        lbl = QLabel(title)
        lbl.setProperty("cssClass", "panelTitle")
        layout.addWidget(lbl)

        if description:
            desc = QLabel(description)
            desc.setProperty("cssClass", "pageDescription")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        widget.setSizePolicy(QSizePolicy.Expanding, widget.sizePolicy().verticalPolicy())
        layout.addWidget(widget)
        return frame

    def set_portfolio_options(self, options: List[PortfolioOption]) -> None:
        current = self.selected_portfolio_source()
        self.combo_portfolio.blockSignals(True)
        self.combo_portfolio.clear()
        for option in options:
            self.combo_portfolio.addItem(option.label, option.code)
        if current:
            idx = self.combo_portfolio.findData(current)
            if idx >= 0:
                self.combo_portfolio.setCurrentIndex(idx)
        self.combo_portfolio.blockSignals(False)
        if self.combo_portfolio.count() and self.combo_portfolio.currentIndex() < 0:
            self.combo_portfolio.setCurrentIndex(0)

    def set_stocks(self, stock_map: Dict[int, str]) -> None:
        items = [
            (display_ticker(ticker), str(stock_id))
            for stock_id, ticker in sorted(stock_map.items(), key=lambda item: item[1])
        ]
        current_selected = [str(stock_id) for stock_id in self.selected_stock_ids()]
        self.stock_combo.set_items(items)
        self.stock_combo.set_selected_data(current_selected)

    def set_benchmarks(self, definitions: List[BenchmarkDefinition]) -> None:
        current = self.selected_benchmarks()
        current_code = current[0] if current else None
        self.combo_benchmark.blockSignals(True)
        self.combo_benchmark.clear()
        for b in definitions:
            self.combo_benchmark.addItem(b.label, b.code)
        if current_code:
            idx = self.combo_benchmark.findData(current_code)
            if idx >= 0:
                self.combo_benchmark.setCurrentIndex(idx)
        self.combo_benchmark.blockSignals(False)
        if self.combo_benchmark.count() and self.combo_benchmark.currentIndex() < 0:
            self.combo_benchmark.setCurrentIndex(0)

    def set_earliest_date(self, earliest: date) -> None:
        self._earliest_date = earliest

    def reset_to_earliest_date(self) -> None:
        start_qdate = QDate(self._earliest_date.year, self._earliest_date.month, self._earliest_date.day)
        self.date_start.blockSignals(True)
        self.date_start.setDate(start_qdate)
        self.date_start.blockSignals(False)
        self.filter_changed.emit()

    def selected_portfolio_source(self) -> str:
        return self.combo_portfolio.currentData()

    def selected_currency_mode(self) -> str:
        idx = self.combo_currency.currentIndex()
        if idx == 1:
            return "USD"
        elif idx == 2:
            return "REAL"
        return "TL"

    def selected_stock_ids(self) -> List[int]:
        return [int(value) for value in self.stock_combo.selected_data()]

    def selected_benchmarks(self) -> List[str]:
        code = self.combo_benchmark.currentData()
        return [code] if code else []

    def date_range(self) -> tuple[date, date]:
        return self.date_start.date().toPyDate(), self.date_end.date().toPyDate()

    def _on_source_changed(self) -> None:
        self.source_changed.emit(self.selected_portfolio_source())
        self.filter_changed.emit()

    def _set_quick_date(self, days: int) -> None:
        end_qdate = QDate.currentDate()
        earliest_qdate = QDate(self._earliest_date.year, self._earliest_date.month, self._earliest_date.day)
        start_qdate = end_qdate.addDays(-days)
        if start_qdate < earliest_qdate:
            start_qdate = earliest_qdate

        self.date_start.blockSignals(True)
        self.date_end.blockSignals(True)
        self.date_start.setDate(start_qdate)
        self.date_end.setDate(end_qdate)
        self.date_start.blockSignals(False)
        self.date_end.blockSignals(False)
        self.filter_changed.emit()

    def _set_all_time(self) -> None:
        start_qdate = QDate(self._earliest_date.year, self._earliest_date.month, self._earliest_date.day)
        self.date_start.blockSignals(True)
        self.date_end.blockSignals(True)
        self.date_start.setDate(start_qdate)
        self.date_end.setDate(QDate.currentDate())
        self.date_start.blockSignals(False)
        self.date_end.blockSignals(False)
        self.filter_changed.emit()
