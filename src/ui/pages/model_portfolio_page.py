from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, Optional

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QDialog
from PyQt5.QtCore import QSize

from .base_page import BasePage
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.cards import InfoCard
from src.ui.widgets.model_portfolio import PortfolioInputDialog, TradeInputDialog
from src.ui.widgets.panels import PortfolioListPanel
from src.ui.widgets.tables import PositionsTable
from src.ui.widgets.toast import Toast

logger = logging.getLogger(__name__)


class ModelPortfolioPage(BasePage):
    def __init__(self, container, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Model Portfoyler"
        self.model_portfolio_service = container.model_portfolio_service
        self.price_lookup_func = price_lookup_func
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}
        self._init_ui()

    def _init_ui(self):
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(IconManager.get_icon("layers", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28))
        header.addWidget(icon_label)

        title_label = QLabel("Model Portfoyler")
        title_label.setProperty("cssClass", "pageTitle")
        header.addWidget(title_label)
        header.addStretch()
        self.main_layout.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(20)
        content.addWidget(self._build_left_panel())
        content.addWidget(self._build_right_panel(), 1)
        self.main_layout.addLayout(content)

    def _build_left_panel(self) -> PortfolioListPanel:
        self.list_panel = PortfolioListPanel()
        self.list_panel.portfolio_selected.connect(self._on_portfolio_selected)
        self.list_panel.new_requested.connect(self._on_new_portfolio)
        self.list_panel.edit_requested.connect(self._on_edit_portfolio)
        self.list_panel.delete_requested.connect(self._on_delete_portfolio)
        return self.list_panel

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        header = QHBoxLayout()
        self.lbl_portfolio_name = QLabel("Bir portfoy secin")
        self.lbl_portfolio_name.setProperty("cssClass", "panelTitleLarge")
        header.addWidget(self.lbl_portfolio_name)
        header.addStretch()

        self.btn_refresh = AnimatedButton(" Fiyat Guncelle")
        self.btn_refresh.setIconName("refresh-cw", color="@COLOR_TEXT_PRIMARY")
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self._on_refresh_prices)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(15)
        self.card_initial = InfoCard("Baslangic", "TL 0", icon_name="wallet")
        self.card_cash = InfoCard("Nakit", "TL 0", icon_name="coins")
        self.card_value = InfoCard("Deger", "TL 0", icon_name="bar-chart-2")
        self.card_pl = InfoCard("K/Z", "TL 0", icon_name="target")
        for card in (self.card_initial, self.card_cash, self.card_value, self.card_pl):
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        label_positions = QLabel("Pozisyonlar")
        label_positions.setProperty("cssClass", "panelTitle")
        layout.addWidget(label_positions)

        self.positions_table = PositionsTable()
        layout.addWidget(self.positions_table)

        trade_row = QHBoxLayout()
        trade_row.addStretch()

        self.btn_buy = AnimatedButton(" Hisse Al")
        self.btn_buy.setIconName("trending-up", color="@COLOR_TEXT_WHITE")
        self.btn_buy.setEnabled(False)
        self.btn_buy.setProperty("cssClass", "successButton")
        self.btn_buy.clicked.connect(lambda: self._on_trade("BUY"))

        self.btn_sell = AnimatedButton(" Hisse Sat")
        self.btn_sell.setIconName("trending-down", color="@COLOR_TEXT_WHITE")
        self.btn_sell.setEnabled(False)
        self.btn_sell.setProperty("cssClass", "dangerButton")
        self.btn_sell.clicked.connect(lambda: self._on_trade("SELL"))

        trade_row.addWidget(self.btn_buy)
        trade_row.addWidget(self.btn_sell)
        layout.addLayout(trade_row)
        return panel

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_portfolios()

    def _load_portfolios(self):
        portfolios = self.model_portfolio_service.get_all_portfolios()
        self.list_panel.refresh(
            portfolios,
            trade_count_func=self.model_portfolio_service.get_trade_count,
        )

    def _on_portfolio_selected(self, portfolio: ModelPortfolio):
        self.current_portfolio_id = portfolio.id
        self.lbl_portfolio_name.setText(portfolio.name)
        for button in (self.btn_buy, self.btn_sell, self.btn_refresh):
            button.setEnabled(True)
        self._update_view()

    def _update_view(self):
        if self.current_portfolio_id is None:
            return

        summary = self.model_portfolio_service.get_portfolio_summary(
            self.current_portfolio_id,
            self.current_price_map,
        )
        self.card_initial.set_value(f"TL {summary['initial_cash']:,.2f}")
        self.card_cash.set_value(f"TL {summary['remaining_cash']:,.2f}")
        self.card_value.set_value(f"TL {summary['total_value']:,.2f}")

        profit_loss = summary["profit_loss"]
        self.card_pl.set_value(f"TL {profit_loss:+,.2f}")
        self.card_pl.set_value_state("positive" if profit_loss >= 0 else "negative")

        positions = self.model_portfolio_service.get_positions_with_details(
            self.current_portfolio_id,
            self.current_price_map,
        )
        self.positions_table.populate(positions)

    def _clear_right_panel(self):
        self.lbl_portfolio_name.setText("Bir portfoy secin")
        self.positions_table.setRowCount(0)
        for button in (self.btn_buy, self.btn_sell, self.btn_refresh):
            button.setEnabled(False)
        for card in (self.card_initial, self.card_cash, self.card_value, self.card_pl):
            card.set_value("TL 0")
            card.set_value_state("neutral")

    def _on_new_portfolio(self):
        dialog = PortfolioInputDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.model_portfolio_service.create_portfolio(**result)
            self._load_portfolios()
            Toast.success(self, f"'{result['name']}' portfoyu olusturuldu.")
        except Exception as exc:
            Toast.error(self, f"Portfoy olusturulamadi: {exc}")

    def _on_edit_portfolio(self):
        if self.current_portfolio_id is None:
            return
        portfolio = self.list_panel.current_portfolio()
        if not portfolio:
            return
        dialog = PortfolioInputDialog(self, portfolio)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.model_portfolio_service.update_portfolio(portfolio_id=self.current_portfolio_id, **result)
            self._load_portfolios()
            self.lbl_portfolio_name.setText(result["name"])
            self._update_view()
            Toast.success(self, "Portfoy guncellendi.")
        except Exception as exc:
            Toast.error(self, f"Portfoy guncellenemedi: {exc}")

    def _on_delete_portfolio(self):
        if self.current_portfolio_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Portfoy Sil",
            "Bu portfoyu silmek istediginizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.model_portfolio_service.delete_portfolio(self.current_portfolio_id)
            self.current_portfolio_id = None
            self._load_portfolios()
            self._clear_right_panel()
            Toast.success(self, "Portfoy silindi.")
        except Exception as exc:
            Toast.error(self, f"Portfoy silinemedi: {exc}")

    def _on_trade(self, side: str):
        if self.current_portfolio_id is None:
            return
        dialog = TradeInputDialog(side, self.price_lookup_func, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.model_portfolio_service.add_trade_by_ticker(
                portfolio_id=self.current_portfolio_id,
                ticker=result["ticker"],
                side=side,
                quantity=result["quantity"],
                price=result["price"],
                trade_date=result["trade_date"],
            )
            self._load_portfolios()
            self._update_view()
            action = "alindi" if side == "BUY" else "satildi"
            Toast.success(self, f"{result['quantity']} lot {result['ticker']} {action}.")
        except ValueError as exc:
            Toast.warning(self, str(exc))
        except Exception as exc:
            Toast.error(self, f"Islem gerceklestirilemedi: {exc}")

    def _on_refresh_prices(self):
        if self.current_portfolio_id is None:
            return
        if not self.price_lookup_func:
            Toast.warning(self, "Fiyat sorgulama fonksiyonu mevcut degil.")
            return
        positions = self.model_portfolio_service.get_positions_with_details(self.current_portfolio_id)
        updated_count = 0
        for pos in positions:
            try:
                result = self.price_lookup_func(pos["ticker"])
                if result:
                    self.current_price_map[pos["stock_id"]] = result.price
                    updated_count += 1
            except Exception as exc:
                logger.error("Fiyat alinamadi: %s - %s", pos["ticker"], exc)
        self._update_view()
        Toast.success(self, f"{updated_count} hisse icin fiyat guncellendi.")

