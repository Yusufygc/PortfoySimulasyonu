# src/ui/pages/model_portfolio/model_portfolio_page.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, List

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from src.ui.pages.base_page import BasePage
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.widgets.dashboard import DateRangeDialog
from src.ui.widgets.shared import Toast

from src.ui.pages.model_portfolio.utils.portfolio_settings import PortfolioSettingsManager
from src.ui.pages.model_portfolio.utils.portfolio_exporter import PortfolioExporter
from src.ui.pages.model_portfolio.utils.portfolio_price_updater import PortfolioPriceUpdater
from src.ui.pages.model_portfolio.utils.model_portfolio_ui_builder import ModelPortfolioUIBuilder
from src.ui.pages.model_portfolio.utils.model_portfolio_actions import ModelPortfolioActions

logger = logging.getLogger(__name__)


class ModelPortfolioPage(BasePage):
    LAST_UPDATE_TOAST_DURATION_MS = 4000

    def __init__(self, container, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.MODEL_PORTFOYLER
        self.model_portfolio_service = container.model_portfolio_service
        self.model_portfolio_excel_export_service = container.model_portfolio_excel_export_service
        self.price_repo = container.price_repo
        self.market_session_service = getattr(container, "bist_market_session_service", None)
        self.price_lookup_func = price_lookup_func
        self.date_range_dialog_cls = DateRangeDialog
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}
        self._last_update_toast_shown_for = None

        self.settings_manager = PortfolioSettingsManager()
        self.exporter = PortfolioExporter(self)
        self.price_updater = PortfolioPriceUpdater(self)
        
        self._actions = ModelPortfolioActions(self)
        self._ui_builder = ModelPortfolioUIBuilder(self)
        self._ui_builder.build_ui()
        self._connect_signals()
        event_bus = getattr(self.container, "event_bus", None)
        if event_bus:
            event_bus.prices_updated.connect(self._on_prices_updated_event)

    def _connect_signals(self) -> None:
        self.list_panel.portfolio_selected.connect(self._on_portfolio_selected)
        self.list_panel.new_requested.connect(self._actions.on_new_portfolio)
        self.list_panel.edit_requested.connect(self._actions.on_edit_portfolio)
        self.list_panel.delete_requested.connect(self._actions.on_delete_portfolio)
        self.list_panel.reordered.connect(self._actions.on_portfolios_reordered)
        
        self.btn_buy.clicked.connect(lambda: self._actions.on_trade("BUY"))
        self.btn_sell.clicked.connect(lambda: self._actions.on_trade("SELL"))
        self.btn_empty_buy.clicked.connect(lambda: self._actions.on_trade("BUY"))
        self.btn_refresh.clicked.connect(self._on_refresh_prices)
        self.btn_capital.clicked.connect(self._actions.on_capital_movement)
        
        self.positions_table.row_double_clicked.connect(self._on_position_double_clicked)

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_portfolios()

    def _load_portfolios(self):
        portfolios = self.model_portfolio_service.get_all_portfolios()
        self.list_panel.refresh(
            portfolios,
            trade_count_func=self.model_portfolio_service.get_active_position_count,
        )
        if not portfolios:
            self.current_portfolio_id = None
            self.current_price_map = {}
            self._clear_right_panel()
            return
        if "settings_manager" not in self.__dict__:
            self.settings_manager = PortfolioSettingsManager()
        selected_id = self.current_portfolio_id or self.settings_manager.get_last_selected_portfolio_id()
        selected_portfolio = self.list_panel.select_portfolio_by_id(selected_id) if selected_id is not None else None
        if selected_portfolio is None:
            selected_portfolio = self.list_panel.select_portfolio_by_id(portfolios[0].id)
        if selected_portfolio:
            self._set_current_portfolio(selected_portfolio, show_toast=True)

    def _on_portfolio_selected(self, portfolio: ModelPortfolio):
        self._set_current_portfolio(portfolio, show_toast=True)

    def _set_current_portfolio(self, portfolio: ModelPortfolio, show_toast: bool = False) -> None:
        self.current_portfolio_id = portfolio.id
        if "settings_manager" not in self.__dict__:
            self.settings_manager = PortfolioSettingsManager()
        self.settings_manager.set_last_selected_portfolio_id(portfolio.id)
        self.current_price_map = self.settings_manager.load_saved_price_map(portfolio.id)
        self._sync_last_update_label()
        self.lbl_portfolio_name.setText(portfolio.name)
        for button in (self.btn_buy, self.btn_refresh, self.btn_report, self.btn_capital, self.btn_empty_buy):
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
        self.card_initial.set_value(f"TL {summary.get('net_capital', summary['initial_cash']):,.2f}")
        self.card_cash.set_value(f"TL {summary['remaining_cash']:,.2f}")
        self.card_value.set_value(f"TL {summary['total_value']:,.2f}")

        profit_loss = round(summary["profit_loss"], 2)
        if profit_loss == 0:
            self.card_pl.set_value(L10N.TL_000)
            self.card_pl.set_value_state("neutral")
        else:
            self.card_pl.set_value(f"TL {profit_loss:+,.2f}")
            self.card_pl.set_value_state("positive" if profit_loss > 0 else "negative")

        positions = self.model_portfolio_service.get_positions_with_details(
            self.current_portfolio_id,
            self.current_price_map,
        )
        previous_close_map = self._build_previous_close_map(positions, date.today())
        self.positions_table.populate(positions, previous_close_map=previous_close_map)
        self.positions_stack.setCurrentWidget(
            self.empty_positions_state if not positions else self.positions_table
        )
        self.btn_sell.setEnabled(bool(positions))

    def _build_previous_close_map(self, positions: List[dict], today: date) -> Dict[int, Decimal]:
        get_last_price_before = getattr(self.price_repo, "get_last_price_before", None)
        if get_last_price_before is None:
            return {}

        previous_close_map: Dict[int, Decimal] = {}
        reference_date = today - timedelta(days=1)
        for position in positions:
            stock_id = position.get("stock_id")
            if stock_id is None:
                continue
            daily_price = get_last_price_before(stock_id, reference_date)
            if daily_price is not None:
                previous_close_map[stock_id] = daily_price.close_price
        return previous_close_map

    def _clear_right_panel(self):
        self.lbl_portfolio_name.setText(L10N.BIR_PORTFOY_SECIN)
        self.lbl_last_update.setText("")
        self.positions_table.setRowCount(0)
        self.positions_stack.setCurrentWidget(self.positions_table)
        for button in (self.btn_buy, self.btn_sell, self.btn_refresh, self.btn_report, self.btn_capital, self.btn_empty_buy):
            button.setEnabled(False)
        for card in (self.card_initial, self.card_cash, self.card_value, self.card_pl):
            card.set_value("TL 0")
            card.set_value_state("neutral")

    # -------------------------------------------------------------------------
    # Proxy / Delege Metotları (Testlerin ve iç yapının bozulmaması için)
    # -------------------------------------------------------------------------

    def _on_position_double_clicked(self, payload: dict) -> None:
        ticker = payload.get("ticker")
        stock_id = payload.get("stock_id")
        if not ticker:
            return
        main_window = self.window()
        if hasattr(main_window, "show_stock_detail"):
            main_window.show_stock_detail(
                ticker,
                stock_id,
                context={
                    "source": "model_portfolio",
                    "portfolio_id": self.current_portfolio_id,
                    "price_map": dict(self.current_price_map),
                },
            )

    def _on_export_today(self) -> None:
        if "exporter" not in self.__dict__:
            self.exporter = PortfolioExporter(self)
        self.exporter.export_today()

    def _on_export_range(self) -> None:
        if "exporter" not in self.__dict__:
            self.exporter = PortfolioExporter(self)
        self.exporter.export_range()

    def _on_refresh_prices(self):
        if "price_updater" not in self.__dict__:
            self.price_updater = PortfolioPriceUpdater(self)
        was_enabled = self.btn_refresh.isEnabled()
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText(L10N.FIYATLAR_GUNCELLENIYOR)
        QApplication.processEvents()
        try:
            self.price_updater.refresh_prices()
        finally:
            self.btn_refresh.setText(L10N.FIYAT_GUNCELLE)
            self.btn_refresh.setEnabled(was_enabled)

    def _on_prices_updated_event(self, prices: Dict[int, Decimal]) -> None:
        if self.current_portfolio_id is None or not prices:
            return
        positions = self.model_portfolio_service.get_positions(self.current_portfolio_id)
        relevant_prices = {
            stock_id: price
            for stock_id, price in prices.items()
            if stock_id in positions
        }
        if not relevant_prices:
            return
        self.current_price_map.update(relevant_prices)
        self._update_view()
        try:
            self.record_last_update_time()
        except RuntimeError:
            pass

    def record_last_update_time(self, updated_at=None):
        if self.current_portfolio_id is None:
            return None

        updated_at = updated_at or datetime.now()
        if "settings_manager" not in self.__dict__:
            self.settings_manager = PortfolioSettingsManager()
        self.settings_manager.save_portfolio_prices_and_time(
            self.current_portfolio_id,
            self.current_price_map,
            updated_at
        )
        self._last_update_toast_shown_for = None
        self._sync_last_update_label(updated_at)
        return updated_at

    def show_last_update_toast_once(self, force: bool = False, detail: str | None = None) -> None:
        if self.current_portfolio_id is None:
            return
        if "settings_manager" not in self.__dict__:
            self.settings_manager = PortfolioSettingsManager()
        updated_at = self.settings_manager.get_last_update_time(self.current_portfolio_id)
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
            duration_ms=self.LAST_UPDATE_TOAST_DURATION_MS,
            position="top",
        )
        self._last_update_toast_shown_for = value

    def _sync_last_update_label(self, updated_at=None) -> None:
        if self.current_portfolio_id is None:
            self.lbl_last_update.setText("")
            return
        if "settings_manager" not in self.__dict__:
            self.settings_manager = PortfolioSettingsManager()
        updated_at = updated_at or self.settings_manager.get_last_update_time(self.current_portfolio_id)
        self.lbl_last_update.setText(
            self._format_last_update_message(updated_at) if updated_at else ""
        )

    @staticmethod
    def _format_last_update_message(updated_at) -> str:
        return f"Son güncelleme: {updated_at.strftime('%d.%m.%Y %H:%M')} (15dk gecikmeli)"
