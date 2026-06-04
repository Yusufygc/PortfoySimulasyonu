# src/ui/pages/model_portfolio/utils/model_portfolio_ui_builder.py

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import (
    QAction,
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QMenu,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt

from src.ui.widgets.shared.controls.icon_label import IconLabel
from src.ui.widgets.model_portfolio import PortfolioListPanel, PositionsTable
from src.ui.widgets.shared import AnimatedButton, InfoCard

if TYPE_CHECKING:
    from src.ui.pages.model_portfolio.model_portfolio_page import ModelPortfolioPage


class ModelPortfolioUIBuilder:
    """Model Portföy sayfası için UI yapılandırmasını yönetir."""

    def __init__(self, page: ModelPortfolioPage) -> None:
        self.page = page

    def build_ui(self) -> None:
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = IconLabel("layers", color="@COLOR_ACCENT", size=28)
        header.addWidget(icon_label)

        title_label = QLabel("Model Portföyler")
        title_label.setProperty("cssClass", "pageTitle")
        header.addWidget(title_label)
        header.addStretch()
        self.page.main_layout.addLayout(header)

        lbl_desc = QLabel("Kendi portföy modellerinizi oluşturun ve performanslarını simüle edin.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setProperty("cssClass", "pageDescription")
        self.page.main_layout.addWidget(lbl_desc)

        content = QHBoxLayout()
        content.setSpacing(20)
        content.addWidget(self._build_left_panel())
        content.addWidget(self._build_right_panel(), 1)
        self.page.main_layout.addLayout(content)

    def _build_left_panel(self) -> PortfolioListPanel:
        self.page.list_panel = PortfolioListPanel()
        return self.page.list_panel

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        header = QHBoxLayout()
        self.page.lbl_portfolio_name = QLabel("Bir portföy seçin")
        self.page.lbl_portfolio_name.setProperty("cssClass", "panelTitleLarge")
        header.addWidget(self.page.lbl_portfolio_name)
        header.addStretch()

        self.page.lbl_last_update = QLabel("")
        self.page.lbl_last_update.setProperty("cssClass", "lastUpdateLabel")
        header.addWidget(self.page.lbl_last_update)

        self.page.btn_refresh = AnimatedButton(" Fiyat Güncelle")
        self.page.btn_refresh.setIconName("refresh-cw", color="@COLOR_TEXT_WHITE")
        self.page.btn_refresh.setProperty("cssClass", "updatePricesBtn")
        self.page.btn_refresh.setEnabled(False)
        header.addWidget(self.page.btn_refresh)

        self.page.btn_report = AnimatedButton(" Rapor Al")
        self.page.btn_report.setIconName("file-text", color="@COLOR_TEXT_PRIMARY")
        self.page.btn_report.setProperty("cssClass", "reportButton")
        self.page.btn_report.setEnabled(False)
        self.page._report_menu = QMenu(self.page.btn_report)
        
        self.page._report_today_action = QAction("Bugün", self.page)
        self.page._report_range_action = QAction("Tarih Aralığı", self.page)
        
        self.page._report_menu.addAction(self.page._report_today_action)
        self.page._report_menu.addAction(self.page._report_range_action)
        self.page.btn_report.setMenu(self.page._report_menu)
        header.addWidget(self.page.btn_report)

        self.page.btn_capital = AnimatedButton(" Sermaye Yönetimi")
        self.page.btn_capital.setIconName("wallet", color="@COLOR_TEXT_PRIMARY")
        self.page.btn_capital.setProperty("cssClass", "reportButton")
        self.page.btn_capital.setEnabled(False)
        header.addWidget(self.page.btn_capital)
        layout.addLayout(header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(15)
        self.page.card_initial = InfoCard("Net Sermaye", "TL 0", icon_name="wallet")
        self.page.card_cash = InfoCard("Nakit", "TL 0", icon_name="coins")
        self.page.card_value = InfoCard("Değer", "TL 0", icon_name="bar-chart-2")
        self.page.card_pl = InfoCard("K/Z", "TL 0", icon_name="target")
        for card in (self.page.card_initial, self.page.card_cash, self.page.card_value, self.page.card_pl):
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        positions_header = QHBoxLayout()
        positions_header.setSpacing(12)

        self.page.label_positions = QLabel("Pozisyonlar")
        self.page.label_positions.setProperty("cssClass", "modelPositionsTitle")
        positions_header.addWidget(self.page.label_positions)
        positions_header.addStretch()

        self.page.btn_buy = AnimatedButton(" Hisse Al")
        self.page.btn_buy.setIconName("trending-up", color="@COLOR_TEXT_WHITE")
        self.page.btn_buy.setEnabled(False)
        self.page.btn_buy.setProperty("cssClass", "successButton")

        self.page.btn_sell = AnimatedButton(" Hisse Sat")
        self.page.btn_sell.setIconName("trending-down", color="@COLOR_TEXT_WHITE")
        self.page.btn_sell.setEnabled(False)
        self.page.btn_sell.setProperty("cssClass", "dangerButton")

        positions_header.addWidget(self.page.btn_buy)
        positions_header.addWidget(self.page.btn_sell)
        self.page._positions_header_layout = positions_header
        layout.addLayout(positions_header)

        self.page.positions_table = PositionsTable()
        self.page.empty_positions_state = self._create_empty_positions_state()
        self.page.positions_stack = QStackedWidget()
        self.page.positions_stack.addWidget(self.page.positions_table)
        self.page.positions_stack.addWidget(self.page.empty_positions_state)
        layout.addWidget(self.page.positions_stack, 1)
        return panel

    def _create_empty_positions_state(self) -> QWidget:
        empty = QFrame()
        empty.setProperty("cssClass", "modelPositionsEmptyState")
        layout = QVBoxLayout(empty)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addStretch()

        icon = IconLabel("trending-up", color="@COLOR_TEXT_MUTED", size=30)
        layout.addWidget(icon, 0, Qt.AlignCenter)

        label = QLabel("Bu portföyde henüz pozisyon yok")
        label.setProperty("cssClass", "modelPositionsEmptyTitle")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.page.btn_empty_buy = AnimatedButton(" Hisse Al")
        self.page.btn_empty_buy.setIconName("trending-up", color="@COLOR_TEXT_WHITE")
        self.page.btn_empty_buy.setProperty("cssClass", "successButton")
        self.page.btn_empty_buy.setEnabled(False)
        layout.addWidget(self.page.btn_empty_buy, 0, Qt.AlignCenter)

        layout.addStretch()
        return empty
