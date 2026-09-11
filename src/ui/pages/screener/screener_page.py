"""
BIST Çoklu Sinyal Tarayıcısı & Teknik Analiz Merkezi.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from src.qt_compat.qtcore import QThreadPool, Qt
from src.qt_compat.qtwidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from src.application.services.analysis.technical.screener import SCREENER_FILTERS
from src.ui.pages.base_page import BasePage
from src.ui.pages.technical.technical_analysis_page import TechnicalAnalysisPage
from src.ui.shared.locale_tr import L10N
from src.ui.worker import Worker

logger = logging.getLogger(__name__)


def _fmt_price(val: Optional[float]) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):,.2f} ₺"
    except Exception:
        return str(val)


class ScreenerPage(BasePage):
    """
    BIST hisselerini teknik stratejiler ve SMA kesişimlerine göre filtreleyen analiz merkezi.
    """

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.NAV_SCREENER
        self._screener_service = getattr(container, "screener_service", None)
        self._pool = QThreadPool()
        self._active_worker: Optional[Worker] = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Başlık Bölümü
        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        lbl_title = QLabel(L10N.SCREENER_PAGE_TITLE)
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel(L10N.SCREENER_DESC)
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)

        header_layout.addLayout(title_col)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Sekmeli Yapı
        self._tabs = QTabWidget()
        self._tabs.setProperty("cssClass", "mainTabWidget")

        # 1. Sekme: Çoklu Sinyal Tarayıcısı
        self._screener_tab = self._build_screener_tab()
        self._tabs.addTab(self._screener_tab, f"⚡ {L10N.SCREENER_TAB_STRATEGIES}")

        # 2. Sekme: Teknik Analiz & Göstergeler (SMA Cross + Detay Grafik)
        self._page_technical = TechnicalAnalysisPage(container=self.container, parent=self)
        self._tabs.addTab(self._page_technical, f"📈 {L10N.SCREENER_TAB_TECHNICAL}")

        layout.addWidget(self._tabs, 1)

    def _build_screener_tab(self) -> QWidget:
        widget = QWidget()
        tab_layout = QVBoxLayout(widget)
        tab_layout.setContentsMargins(0, 8, 0, 0)
        tab_layout.setSpacing(10)

        # Filtre ve Kontrol Çubuğu
        control_card = QFrame()
        control_card.setProperty("cssClass", "card")
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(10)

        lbl_filter = QLabel(f"{L10N.STRATEJI}:")
        lbl_filter.setProperty("cssClass", "filterLabel")
        control_layout.addWidget(lbl_filter)

        self._filter_combo = QComboBox()
        self._filter_combo.setProperty("cssClass", "customComboBox")
        self._filter_combo.addItem(L10N.TUM_STRATEJILER, userData=None)
        for k, v in SCREENER_FILTERS.items():
            self._filter_combo.addItem(v.label, userData=k)
        control_layout.addWidget(self._filter_combo)

        self._btn_scan = QPushButton(L10N.SCREENER_RUN_BUTTON)
        self._btn_scan.setProperty("cssClass", "primaryButton")
        self._btn_scan.clicked.connect(self._on_scan_clicked)
        control_layout.addWidget(self._btn_scan)

        self._status_label = QLabel(L10N.SCREENER_READY)
        self._status_label.setProperty("cssClass", "pageDescription")
        control_layout.addWidget(self._status_label)

        control_layout.addStretch()
        tab_layout.addWidget(control_card)

        # Sonuçlar Tablosu
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([f"{L10N.HISSE} Kodu", L10N.STRATEJI, "Son Fiyat"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setProperty("cssClass", "customTable")
        self._table.cellDoubleClicked.connect(self._on_row_double_clicked)
        tab_layout.addWidget(self._table, 1)

        return widget

    def _on_scan_clicked(self) -> None:
        if self._screener_service is None:
            self._status_label.setText(L10N.SCREENER_SERVICE_NOT_FOUND)
            return

        selected_key = self._filter_combo.currentData()
        filter_keys = [selected_key] if selected_key else None

        self._btn_scan.setEnabled(False)
        self._status_label.setText(L10N.SCREENER_RUNNING)

        worker = Worker(self._screener_service.scan, filter_keys=filter_keys)
        worker.signals.result.connect(self._on_scan_done)
        worker.signals.error.connect(self._on_scan_error)
        worker.signals.cleanup.connect(self._on_scan_cleanup)
        self._active_worker = worker
        self._pool.start(worker)

    def _on_scan_done(self, matches: list) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(matches))

        for row_idx, match in enumerate(matches):
            item_ticker = QTableWidgetItem(match.ticker)
            item_ticker.setTextAlignment(Qt.AlignCenter)
            item_ticker.setData(Qt.UserRole, match.ticker)

            item_strat = QTableWidgetItem(match.filter_label)
            item_strat.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_price = QTableWidgetItem(_fmt_price(match.close_price))
            item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self._table.setItem(row_idx, 0, item_ticker)
            self._table.setItem(row_idx, 1, item_strat)
            self._table.setItem(row_idx, 2, item_price)

        self._table.setSortingEnabled(True)
        self._status_label.setText(f"Tarama tamamlandı: {len(matches)} hisse sinyal verdi.")

    def _on_scan_error(self, err_tuple) -> None:
        logger.error("Screener tarama hatası: %s", err_tuple[1])
        self._status_label.setText(f"Hata oluştu: {err_tuple[1]}")

    def _on_scan_cleanup(self) -> None:
        self._btn_scan.setEnabled(True)
        self._active_worker = None

    def _on_row_double_clicked(self, row: int, col: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        ticker = item.data(Qt.UserRole) or item.text().strip()
        if ticker and hasattr(self._page_technical, "load_ticker"):
            self._page_technical.load_ticker(ticker)
            self._tabs.setCurrentIndex(1)

    def on_page_enter(self) -> None:
        pass

    def on_page_leave(self) -> None:
        self._active_worker = None
        if hasattr(self._page_technical, "on_page_leave"):
            self._page_technical.on_page_leave()
