"""
Hisse 360 & Temel Finansal Araştırma Sayfası — Bilanço, Rasyolar ve KAP Ortaklık Yapısı.
"""
from __future__ import annotations

import logging

from src.qt_compat.qtwidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)
from src.ui.pages.base_page import BasePage
from src.ui.pages.financials.financials_page import FinancialsPage
from src.ui.pages.shareholders.shareholders_page import ShareholdersPage
from src.ui.shared.locale_tr import L10N

logger = logging.getLogger(__name__)


class Stock360Page(BasePage):
    """
    Hisse 360 temel analiz araştırma sayfası.
    
    Bünyesinde 2 ana finansal modülü sekmeler halinde barındırır:
    1. Bilanço & Finansallar (Çeyreklik tablolar, rasyolar, büyüme oranları)
    2. KAP Ortaklık Yapısı (Pay sahipliği tarihçesi, halka açıklık)
    """

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.NAV_STOCK_360
        self._current_ticker: str = ""

        self._init_ui()

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Üst Arama & Kontrol Çubuğu
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_title = QLabel(L10N.STOCK_360_TITLE)
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel(L10N.STOCK_360_DESC)
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        # Ortak Hisse Arama Çubuğu
        search_box = QHBoxLayout()
        search_box.setSpacing(6)

        lbl_search = QLabel(f"{L10N.HISSE}:")
        lbl_search.setProperty("cssClass", "pageDescription")
        search_box.addWidget(lbl_search)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(L10N.STOCK_360_SEARCH_PLACEHOLDER)
        self._search_input.setMaximumWidth(160)
        self._search_input.returnPressed.connect(self._on_search_clicked)
        search_box.addWidget(self._search_input)

        self._btn_search = QPushButton(L10N.STOCK_360_SEARCH_BUTTON)
        self._btn_search.setProperty("cssClass", "primaryButton")
        self._btn_search.clicked.connect(self._on_search_clicked)
        search_box.addWidget(self._btn_search)

        header_layout.addLayout(search_box)
        layout.addLayout(header_layout)

        # Alt Sekmeli Görünüm
        self._tabs = QTabWidget()
        self._tabs.setProperty("cssClass", "mainTabWidget")

        # 1. Sekme: Bilanço ve Finansallar
        self._page_financials = FinancialsPage(container=self.container, parent=self)
        self._tabs.addTab(self._page_financials, f"📊 {L10N.BILANCO_VE_FINANSALLAR}")

        # 2. Sekme: Ortaklık Yapısı
        self._page_shareholders = ShareholdersPage(container=self.container, parent=self)
        self._tabs.addTab(self._page_shareholders, f"👥 {L10N.ORTAKLIK_YAPISI}")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, 1)

    def _on_search_clicked(self) -> None:
        ticker = self._search_input.text().strip().upper()
        if not ticker:
            return
        self.set_stock(ticker)

    def set_stock(self, ticker: str) -> None:
        """Belirtilen hisseyi tüm sekmelere yükle veya aktif sekmeyi güncelle."""
        ticker = ticker.strip().upper()
        if not ticker:
            return
        self._current_ticker = ticker
        self._search_input.setText(ticker)

        current_idx = self._tabs.currentIndex()
        if current_idx == 0 and hasattr(self._page_financials, "load_ticker"):
            self._page_financials.load_ticker(ticker)
        elif current_idx == 1 and hasattr(self._page_shareholders, "load_ticker"):
            self._page_shareholders.load_ticker(ticker)

    def _on_tab_changed(self, index: int) -> None:
        """Sekme değiştiğinde önceden girilen hisse varsa o sekmeye de yükle."""
        if not self._current_ticker:
            return
        if index == 0 and hasattr(self._page_financials, "load_ticker"):
            self._page_financials.load_ticker(self._current_ticker)
        elif index == 1 and hasattr(self._page_shareholders, "load_ticker"):
            self._page_shareholders.load_ticker(self._current_ticker)

    def on_page_enter(self) -> None:
        pass

    def on_page_leave(self) -> None:
        if hasattr(self._page_financials, "on_page_leave"):
            self._page_financials.on_page_leave()
        if hasattr(self._page_shareholders, "on_page_leave"):
            self._page_shareholders.on_page_leave()

    def closeEvent(self, event) -> None:
        self.on_page_leave()
        super().closeEvent(event)
