# src/ui/pages/model_portfolio/model_portfolio_page.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, List

from PyQt5.QtCore import QTimer, QThreadPool
from PyQt5.QtWidgets import QApplication

from src.ui.pages.base_page import BasePage
from src.ui.shared.last_update_mixin import LastUpdateDisplayMixin
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.widgets.dashboard import DateRangeDialog
from src.ui.widgets.shared import Toast

from src.ui.pages.model_portfolio.utils.portfolio_settings import PortfolioSettingsManager
from src.ui.pages.model_portfolio.utils.portfolio_exporter import PortfolioExporter
from src.ui.pages.model_portfolio.utils.portfolio_price_updater import PortfolioPriceUpdater
from src.ui.pages.model_portfolio.utils.model_portfolio_ui_builder import ModelPortfolioUIBuilder
from src.ui.pages.model_portfolio.utils.model_portfolio_actions import ModelPortfolioActions
from src.ui.pages.model_portfolio.model_portfolio_presenter import ModelPortfolioPresenter

logger = logging.getLogger(__name__)


class ModelPortfolioPage(BasePage, LastUpdateDisplayMixin):
    LAST_UPDATE_TOAST_DURATION_MS = 4000

    def __init__(self, container, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.MODEL_PORTFOYLER
        self.model_portfolio_service = container.model_portfolio_service
        self.model_portfolio_excel_export_service = container.model_portfolio_excel_export_service
        self.price_data_health_service = getattr(container, "price_data_health_service", None)
        self.latest_price_repo = getattr(container, "latest_price_repo", None)
        self.price_repo = container.price_repo
        self.market_session_service = getattr(container, "bist_market_session_service", None)
        self.price_lookup_func = price_lookup_func
        self.date_range_dialog_cls = DateRangeDialog
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}
        self._last_update_toast_shown_for = None
        self.threadpool = QThreadPool()

        self.settings_manager = PortfolioSettingsManager()
        self.exporter = PortfolioExporter(self)
        self.price_updater = PortfolioPriceUpdater(self)
        
        self._actions = ModelPortfolioActions(self)
        self._presenter = ModelPortfolioPresenter(self)
        self._ui_builder = ModelPortfolioUIBuilder(self)
        self._ui_builder.build_ui()
        self._connect_signals()
        event_bus = getattr(self.container, "event_bus", None)
        if event_bus:
            event_bus.prices_updated.connect(self._presenter.on_prices_updated_event)

    def _connect_signals(self) -> None:
        self.list_panel.portfolio_selected.connect(self._on_portfolio_selected)
        self.list_panel.new_requested.connect(self._actions.on_new_portfolio)
        self.list_panel.edit_requested.connect(self._actions.on_edit_portfolio)
        self.list_panel.delete_requested.connect(self._actions.on_delete_portfolio)
        self.list_panel.reordered.connect(self._actions.on_portfolios_reordered)
        
        self.btn_new_trade.clicked.connect(self._actions.on_trade)
        self.btn_empty_trade.clicked.connect(self._actions.on_trade)
        self.btn_refresh.clicked.connect(self._on_refresh_prices)
        self.btn_capital.clicked.connect(self._actions.on_capital_movement)
        self._report_today_action.triggered.connect(self._on_export_today)
        self._report_range_action.triggered.connect(self._on_export_range)
        
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
        self.settings_manager.set_last_selected_portfolio_id(portfolio.id)
        self.current_price_map = self._presenter.load_current_price_map(portfolio.id)
        self._sync_last_update_label()
        self.lbl_portfolio_name.setText(portfolio.name)
        for button in (self.btn_new_trade, self.btn_refresh, self.btn_report, self.btn_capital):
            button.setEnabled(True)
        self.btn_empty_trade.setEnabled(True)
        self._presenter.update_view()
        if show_toast:
            QTimer.singleShot(0, self.show_last_update_toast_once)

    def _update_view(self) -> None:
        """Presenter'a delege edilen görünüm güncelleme proxy metodu."""
        self._presenter.update_view()

    def _clear_right_panel(self):
        self.lbl_portfolio_name.setText(L10N.BIR_PORTFOY_SECIN)
        self.lbl_last_update.setText("")
        self.positions_table.setRowCount(0)
        self.positions_stack.setCurrentWidget(self.positions_table)
        for button in (self.btn_new_trade, self.btn_refresh, self.btn_report, self.btn_capital, self.btn_empty_trade):
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
        self.exporter.export_today()

    def _on_export_range(self) -> None:
        self.exporter.export_range()

    def _on_refresh_prices(self):
        was_enabled = self.btn_refresh.isEnabled()
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText(L10N.FIYATLAR_GUNCELLENIYOR)
        # We will dispatch to async worker via actions
        self._actions.on_update_prices()

    def _get_last_update_context_id(self) -> str:
        return str(self.current_portfolio_id) if self.current_portfolio_id is not None else ""

    def _get_last_update_time(self):
        if self.current_portfolio_id is None:
            return None
        return self.settings_manager.get_last_update_time(self.current_portfolio_id)

    def _save_last_update_time(self, updated_at):
        if self.current_portfolio_id is not None:
            self.settings_manager.save_portfolio_last_update_time(self.current_portfolio_id, updated_at)
