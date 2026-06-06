from src.ui.shared.locale_tr import L10N
import logging
from decimal import Decimal

from PyQt5.QtCore import QModelIndex, QSettings, QThreadPool, QTimer, QSize
from PyQt5.QtWidgets import QAction, QHBoxLayout, QLabel, QMenu, QVBoxLayout

from src.ui.pages.base_page import BasePage
from src.ui.shared.last_update_mixin import LastUpdateDisplayMixin
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.dashboard import CapitalDialog, DateRangeDialog, NewStockTradeDialog
from src.ui.widgets.shared import AnimatedButton, Toast

from .dashboard_actions import DashboardActions
from .dashboard_portfolio_table import DashboardPortfolioTable
from .dashboard_presenter import DashboardPresenter
from .dashboard_summary_cards import DashboardSummaryCards

logger = logging.getLogger(__name__)

LAST_UPDATE_SETTINGS_KEY    = "dashboard/last_price_update_at"
WEEKLY_RETURN_SETTINGS_KEY  = "dashboard/weekly_return_pct"
MONTHLY_RETURN_SETTINGS_KEY = "dashboard/monthly_return_pct"
LAST_UPDATE_TOAST_DURATION_MS = 4000


class DashboardPage(BasePage, LastUpdateDisplayMixin):
    def __init__(
        self,
        container,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.DASHBOARD

        self.portfolio_service = container.portfolio_service
        self.cash_movement_service = container.cash_movement_service
        self.return_calc_service = container.return_calc_service
        self.update_coordinator = container.update_coordinator
        self.stock_repo = container.stock_repo
        self.price_repo = container.price_repo
        self.latest_price_repo = getattr(container, "latest_price_repo", None)
        self.reset_service = container.reset_service
        self.market_client = container.market_client
        self.market_session_service = getattr(container, "bist_market_session_service", None)
        self.excel_export_service = container.excel_export_service
        self.trade_entry_service = container.trade_entry_service
        self.corporate_action_service = container.corporate_action_service
        self.backfill_service = container.backfill_service
        self.price_lookup_func = price_lookup_func

        self.new_trade_dialog_cls = NewStockTradeDialog
        self.date_range_dialog_cls = DateRangeDialog
        self.capital_dialog_cls = CapitalDialog
        self.threadpool = QThreadPool()
        self._capital = Decimal("0")
        self.portfolio_model = None
        self._is_refreshing = False
        self._last_trade_result = None
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._last_update_toast_shown_for = None
        self._last_invalid_trade_warning_count = 0

        self._presenter = DashboardPresenter(self)
        self._actions = DashboardActions(self, self._presenter)

        self._init_ui()
        if self.container.event_bus:
            self.container.event_bus.prices_updated.connect(self._presenter.on_prices_updated_event)

    def _init_ui(self):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(
            IconManager.get_icon("layout-dashboard", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28)
        )
        title_row.addWidget(icon_label)

        title_label = QLabel(L10N.DASHBOARD)
        title_label.setProperty("cssClass", "pageTitle")
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_layout.addLayout(title_row)

        description_label = QLabel(L10N.PORTFOYUNUZUN_OZETINI_RAPORLARINI_VE_GUNCELLEME)
        description_label.setProperty("cssClass", "pageDescription")
        description_label.setWordWrap(True)
        title_layout.addWidget(description_label)

        header_layout.addLayout(title_layout, 1)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(6)

        primary_actions_layout = QHBoxLayout()
        primary_actions_layout.setSpacing(10)

        self.btn_new_trade = AnimatedButton(L10N.YENI_ISLEM)
        self.btn_new_trade.setIconName("plus", color="@COLOR_TEXT_WHITE")
        self.btn_new_trade.setProperty("cssClass", "primaryButton")
        self.btn_new_trade.clicked.connect(self._actions.on_new_trade)

        self.btn_update_prices = AnimatedButton(L10N.FIYATLARI_GUNCELLE)
        self.btn_update_prices.setIconName("refresh-cw", color="@COLOR_TEXT_WHITE")
        self.btn_update_prices.setProperty("cssClass", "updatePricesBtn")
        self.btn_update_prices.clicked.connect(self._actions.on_update_prices)

        self.lbl_last_update = QLabel("")
        self.lbl_last_update.setProperty("cssClass", "lastUpdateLabel")

        self.btn_capital = AnimatedButton(L10N.SERMAYE_YONETIMI)
        self.btn_capital.setIconName("coins", color="@COLOR_TEXT_WHITE")
        self.btn_capital.clicked.connect(self._actions.on_capital_management)
        self.btn_capital.setProperty("cssClass", "capitalButton")

        self.btn_report = AnimatedButton(L10N.RAPOR_AL)
        self.btn_report.setIconName(L10N.FILETEXT, color="@COLOR_TEXT_PRIMARY")
        self.btn_report.setProperty("cssClass", "reportButton")
        self._report_menu = QMenu(self.btn_report)
        self._report_today_action = QAction("Bug├╝n", self)
        self._report_today_action.triggered.connect(self._actions.on_export_today)
        self._report_range_action = QAction(L10N.TARIH_ARALIGI, self)
        self._report_range_action.triggered.connect(self._actions.on_export_range)
        self._report_menu.addAction(self._report_today_action)
        self._report_menu.addAction(self._report_range_action)
        self.btn_report.setMenu(self._report_menu)

        primary_actions_layout.addWidget(self.btn_new_trade)
        primary_actions_layout.addWidget(self.btn_update_prices)
        primary_actions_layout.addWidget(self.btn_capital)
        primary_actions_layout.addWidget(self.btn_report)
        primary_actions_layout.addStretch()
        actions_layout.addLayout(primary_actions_layout)

        last_update_row = QHBoxLayout()
        last_update_row.setSpacing(0)
        last_update_row.addStretch()
        last_update_row.addWidget(self.lbl_last_update)
        actions_layout.addLayout(last_update_row)

        header_layout.addLayout(actions_layout, 0)
        self.main_layout.addLayout(header_layout)

        self.summary_cards = DashboardSummaryCards()

        self.main_layout.addWidget(self.summary_cards)

        self.portfolio_table_widget = DashboardPortfolioTable()
        self.portfolio_table_widget.row_double_clicked.connect(self._on_table_double_clicked)
        self.portfolio_table_widget.corporate_action_requested.connect(self._actions.on_corporate_action)
        self.main_layout.addWidget(self.portfolio_table_widget)

    def on_page_enter(self):
        self._presenter.load_capital()
        self.refresh_data()

        # Kay─▒tl─▒ son de─şeri an─▒nda g├Âster; sonra DB'den taze hesapla
        weekly_saved, monthly_saved = self._load_saved_returns()
        if weekly_saved is not None or monthly_saved is not None:
            self.summary_cards.update_returns(weekly_saved, monthly_saved)
        self._presenter.update_returns()

        self._sync_last_update_label()
        QTimer.singleShot(0, self.show_last_update_toast_once)

    def refresh_data(self):
        self._presenter.refresh_data()

    def _save_last_update_time(self, updated_at):
        value = updated_at.isoformat(timespec="seconds")
        self._settings.setValue(LAST_UPDATE_SETTINGS_KEY, value)
        self._settings.sync()

    def _get_last_update_time(self):
        from datetime import datetime

        value = self._settings.value(LAST_UPDATE_SETTINGS_KEY, "", type=str)
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _save_returns(self, weekly_pct, monthly_pct) -> None:
        if weekly_pct is not None:
            self._settings.setValue(WEEKLY_RETURN_SETTINGS_KEY, weekly_pct)
        if monthly_pct is not None:
            self._settings.setValue(MONTHLY_RETURN_SETTINGS_KEY, monthly_pct)
        self._settings.sync()

    def _load_saved_returns(self):
        w = self._settings.value(WEEKLY_RETURN_SETTINGS_KEY,  None)
        m = self._settings.value(MONTHLY_RETURN_SETTINGS_KEY, None)
        return (float(w) if w is not None else None,
                float(m) if m is not None else None)

    def _on_table_double_clicked(self, index: QModelIndex):
        if not index.isValid() or self.portfolio_model is None:
            return

        row = index.row()
        if row < 0 or row >= self.portfolio_model.rowCount():
            return

        position = self.portfolio_model.get_position(row)
        stock = self.stock_repo.get_stock_by_id(position.stock_id)
        ticker = stock.ticker if stock else None

        main_window = self.window()
        if hasattr(main_window, "show_stock_detail"):
            main_window.show_stock_detail(ticker, position.stock_id)
