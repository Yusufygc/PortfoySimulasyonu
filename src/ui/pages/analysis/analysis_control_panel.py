from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from PyQt5.QtCore import QDate, pyqtSignal
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

from .benchmark_chip_group import BenchmarkChipGroup
from .checkable_combo_box import CheckableComboBox


class AnalysisControlPanel(QFrame):
    filter_changed = pyqtSignal()
    source_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFramePadded")
        self.setMinimumWidth(500)
        self.setMaximumWidth(560)
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

        self.compare_combo = CheckableComboBox("Kar\u015f\u0131la\u015ft\u0131rma portf\u00f6yleri se\u00e7in")
        self.compare_combo.selection_changed.connect(self.filter_changed.emit)
        layout.addWidget(
            self._wrap_field(
                "Kar\u015f\u0131la\u015ft\u0131rma Portf\u00f6yleri",
                self.compare_combo,
                "Portf\u00f6y kar\u015f\u0131la\u015ft\u0131rmas\u0131na dahil edilecek di\u011fer portf\u00f6yler.",
            )
        )

        self.combo_view_mode = self._create_combo_box("G\u00f6r\u00fcn\u00fcm")
        self.combo_view_mode.addItem("Portf\u00f6y \u00d6ncelikli", "portfolio")
        self.combo_view_mode.addItem("Hisse Kar\u015f\u0131la\u015ft\u0131rma", "stocks")
        self.combo_view_mode.currentIndexChanged.connect(self.filter_changed.emit)
        layout.addWidget(self._wrap_field("G\u00f6r\u00fcn\u00fcm", self.combo_view_mode))

        self.stock_combo = CheckableComboBox("Hisse se\u00e7in")
        self.stock_combo.selection_changed.connect(self.filter_changed.emit)
        layout.addWidget(
            self._wrap_field(
                "Hisse Se\u00e7imi",
                self.stock_combo,
                "Se\u00e7ilen portf\u00f6ydeki hisseler.",
            )
        )

        dates_row = QHBoxLayout()
        dates_row.setSpacing(10)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setProperty("cssClass", "tradeInputNormal")
        self.date_start.setMinimumHeight(38)
        self.date_start.setDate(QDate.currentDate().addMonths(-3))
        self.date_start.dateChanged.connect(self.filter_changed.emit)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setProperty("cssClass", "tradeInputNormal")
        self.date_end.setMinimumHeight(38)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.filter_changed.emit)

        dates_row.addWidget(self._wrap_field("Ba\u015flang\u0131\u00e7", self.date_start), 1)
        dates_row.addWidget(self._wrap_field("Biti\u015f", self.date_end), 1)
        layout.addLayout(dates_row)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        for label, days in [("1A", 30), ("3A", 90), ("6A", 180), ("1Y", 365)]:
            button = QPushButton(label)
            button.setProperty("cssClass", "quickDateBtn")
            button.clicked.connect(lambda _, d=days: self._set_quick_date(d))
            quick_row.addWidget(button)

        btn_all = QPushButton("T\u00fcm\u00fc")
        btn_all.setProperty("cssClass", "quickDateBtn")
        btn_all.clicked.connect(self._set_all_time)
        quick_row.addWidget(btn_all)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        self.benchmark_chips = BenchmarkChipGroup()
        self.benchmark_chips.selection_changed.connect(self.filter_changed.emit)
        layout.addWidget(self._wrap_field("Benchmark Se\u00e7imi", self.benchmark_chips))
        layout.addStretch()

    def _create_combo_box(self, _placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setProperty("cssClass", "customComboBox")
        combo.setMinimumHeight(38)
        combo.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
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

    def set_comparison_portfolios(self, options: List[PortfolioOption]) -> None:
        current_source = self.selected_portfolio_source()
        items = [(option.label, option.code) for option in options if option.code != current_source]
        self.compare_combo.set_items(items)

    def set_stocks(self, stock_map: Dict[int, str]) -> None:
        items = [(ticker, str(stock_id)) for stock_id, ticker in sorted(stock_map.items(), key=lambda item: item[1])]
        current_selected = [str(stock_id) for stock_id in self.selected_stock_ids()]
        self.stock_combo.set_items(items)
        self.stock_combo.set_selected_data(current_selected)

    def set_benchmarks(self, definitions: List[BenchmarkDefinition]) -> None:
        self.benchmark_chips.set_benchmarks(definitions)

    def set_earliest_date(self, earliest: date) -> None:
        self._earliest_date = earliest

    def selected_portfolio_source(self) -> str:
        return self.combo_portfolio.currentData()

    def selected_comparison_sources(self) -> List[str]:
        return self.compare_combo.selected_data()

    def selected_stock_ids(self) -> List[int]:
        return [int(value) for value in self.stock_combo.selected_data()]

    def selected_benchmarks(self) -> List[str]:
        return self.benchmark_chips.selected_codes()

    def view_mode(self) -> str:
        return self.combo_view_mode.currentData()

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
