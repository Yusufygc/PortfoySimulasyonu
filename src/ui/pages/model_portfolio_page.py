from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QDialog
from PyQt5.QtCore import QSettings, QTimer, QSize

from .base_page import BasePage
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.model_portfolio import PortfolioInputDialog, PortfolioListPanel, PositionsTable, TradeInputDialog
from src.ui.widgets.shared import AnimatedButton, InfoCard, Toast

logger = logging.getLogger(__name__)

LAST_SELECTED_PORTFOLIO_KEY = "model_portfolios/last_selected_id"
LAST_UPDATE_TOAST_DURATION_MS = 4000


class ModelPortfolioPage(BasePage):
    def __init__(self, container, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Model Portfoyler"
        self.model_portfolio_service = container.model_portfolio_service
        self.price_lookup_func = price_lookup_func
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._last_update_toast_shown_for = None
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

        self.lbl_last_update = QLabel("")
        self.lbl_last_update.setProperty("cssClass", "lastUpdateLabel")
        header.addWidget(self.lbl_last_update)

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
        selected_id = self.current_portfolio_id or self._get_last_selected_portfolio_id()
        if selected_id is None:
            return
        selected_portfolio = self.list_panel.select_portfolio_by_id(selected_id)
        if selected_portfolio:
            self._set_current_portfolio(selected_portfolio, show_toast=True)

    def _on_portfolio_selected(self, portfolio: ModelPortfolio):
        self._set_current_portfolio(portfolio, show_toast=True)

    def _set_current_portfolio(self, portfolio: ModelPortfolio, show_toast: bool = False) -> None:
        self.current_portfolio_id = portfolio.id
        self._settings.setValue(LAST_SELECTED_PORTFOLIO_KEY, portfolio.id)
        self._settings.sync()
        self.current_price_map = self._load_saved_price_map(portfolio.id)
        self._sync_last_update_label()
        self.lbl_portfolio_name.setText(portfolio.name)
        for button in (self.btn_buy, self.btn_sell, self.btn_refresh):
            button.setEnabled(True)
        self._update_view()
        if show_toast:
            QTimer.singleShot(0, self.show_last_update_toast_once)

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
        self.lbl_last_update.setText("")
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
            portfolio = self.model_portfolio_service.create_portfolio(**result)
            if portfolio and portfolio.id is not None:
                self.current_portfolio_id = portfolio.id
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
            self._settings.remove(self._price_map_settings_key(self.current_portfolio_id))
            self._settings.remove(self._last_update_settings_key(self.current_portfolio_id))
            self._settings.remove(LAST_SELECTED_PORTFOLIO_KEY)
            self._settings.sync()
            self.current_portfolio_id = None
            self.current_price_map = {}
            self._last_update_toast_shown_for = None
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
        if updated_count <= 0:
            Toast.warning(
                self,
                "Guncellenecek fiyat bulunamadi.",
                duration_ms=LAST_UPDATE_TOAST_DURATION_MS,
                position="top",
            )
            return
        self.record_last_update_time()
        self.show_last_update_toast_once(
            force=True,
            detail=f"{updated_count} hisse icin fiyat guncellendi.",
        )

    def record_last_update_time(self, updated_at=None):
        if self.current_portfolio_id is None:
            return None

        updated_at = updated_at or datetime.now()
        self._settings.setValue(
            self._price_map_settings_key(self.current_portfolio_id),
            self._serialize_price_map(self.current_price_map),
        )
        self._settings.setValue(
            self._last_update_settings_key(self.current_portfolio_id),
            updated_at.isoformat(timespec="seconds"),
        )
        self._settings.sync()
        self._last_update_toast_shown_for = None
        self._sync_last_update_label(updated_at)
        return updated_at

    def show_last_update_toast_once(self, force: bool = False, detail: str | None = None) -> None:
        updated_at = self._get_last_update_time()
        if updated_at is None:
            return

        value = f"{self.current_portfolio_id}:{updated_at.isoformat(timespec='seconds')}"
        if not force and self._last_update_toast_shown_for == value:
            return

        message = self._format_last_update_message(updated_at)
        if detail:
            message = f"{message} - {detail}"
        Toast.info(
            self,
            message,
            duration_ms=LAST_UPDATE_TOAST_DURATION_MS,
            position="top",
        )
        self._last_update_toast_shown_for = value

    def _sync_last_update_label(self, updated_at=None) -> None:
        updated_at = updated_at or self._get_last_update_time()
        self.lbl_last_update.setText(
            self._format_last_update_message(updated_at) if updated_at else ""
        )

    def _get_last_selected_portfolio_id(self) -> Optional[int]:
        value = self._settings.value(LAST_SELECTED_PORTFOLIO_KEY, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _get_last_update_time(self):
        if self.current_portfolio_id is None:
            return None
        value = self._settings.value(
            self._last_update_settings_key(self.current_portfolio_id),
            "",
            type=str,
        )
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _load_saved_price_map(self, portfolio_id: int) -> Dict[int, Decimal]:
        value = self._settings.value(self._price_map_settings_key(portfolio_id), "", type=str)
        if not value:
            return {}
        try:
            raw_map = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

        price_map: Dict[int, Decimal] = {}
        for stock_id, price in raw_map.items():
            try:
                price_map[int(stock_id)] = Decimal(str(price))
            except Exception:
                continue
        return price_map

    @staticmethod
    def _serialize_price_map(price_map: Dict[int, Decimal]) -> str:
        return json.dumps({str(stock_id): str(price) for stock_id, price in price_map.items()})

    @staticmethod
    def _price_map_settings_key(portfolio_id: int) -> str:
        return f"model_portfolios/{portfolio_id}/price_map"

    @staticmethod
    def _last_update_settings_key(portfolio_id: int) -> str:
        return f"model_portfolios/{portfolio_id}/last_price_update_at"

    @staticmethod
    def _format_last_update_message(updated_at) -> str:
        return f"Son guncelleme: {updated_at.strftime('%d.%m.%Y %H:%M')} (15dk gecikmeli)"
