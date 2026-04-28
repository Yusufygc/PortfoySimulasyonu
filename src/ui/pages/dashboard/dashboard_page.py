import logging
from decimal import Decimal

from PyQt5.QtCore import QModelIndex, QSettings, QThreadPool, QTimer, QSize
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from src.ui.pages.base_page import BasePage
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.dashboard import BackfillDialog, CapitalDialog, DateRangeDialog, NewStockTradeDialog
from src.ui.widgets.shared import AnimatedButton, Toast

from .dashboard_actions import DashboardActions
from .dashboard_portfolio_table import DashboardPortfolioTable
from .dashboard_presenter import DashboardPresenter
from .dashboard_summary_cards import DashboardSummaryCards

logger = logging.getLogger(__name__)

LAST_UPDATE_SETTINGS_KEY = "dashboard/last_price_update_at"
LAST_UPDATE_TOAST_DURATION_MS = 4000


class DashboardPage(BasePage):
    def __init__(
        self,
        container,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.container = container
        self.page_title = "Dashboard"

        self.portfolio_service = container.portfolio_service
        self.return_calc_service = container.return_calc_service
        self.update_coordinator = container.update_coordinator
        self.stock_repo = container.stock_repo
        self.reset_service = container.reset_service
        self.market_client = container.market_client
        self.excel_export_service = container.excel_export_service
        self.trade_entry_service = container.trade_entry_service
        self.price_lookup_func = price_lookup_func
        self.backfill_service = container.backfill_service

        self.new_trade_dialog_cls = NewStockTradeDialog
        self.date_range_dialog_cls = DateRangeDialog
        self.capital_dialog_cls = CapitalDialog
        self.backfill_dialog_cls = BackfillDialog
        self.threadpool = QThreadPool()
        self._capital = Decimal("0")
        self.portfolio_model = None
        self._is_refreshing = False
        self._last_trade_result = None
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._last_update_toast_shown_for = None

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

        title_label = QLabel("Dashboard")
        title_label.setProperty("cssClass", "pageTitle")
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_layout.addLayout(title_row)

        description_label = QLabel("Portfoyunuzun ozetini, raporlarini ve guncelleme aksiyonlarini tek yerden yonetin.")
        description_label.setProperty("cssClass", "pageDescription")
        description_label.setWordWrap(True)
        title_layout.addWidget(description_label)

        header_layout.addLayout(title_layout, 1)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(6)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.btn_new_trade = AnimatedButton(" Yeni Islem")
        self.btn_new_trade.setIconName("plus", color="@COLOR_TEXT_WHITE")
        self.btn_new_trade.setProperty("cssClass", "primaryButton")
        self.btn_new_trade.clicked.connect(self._actions.on_new_trade)

        self.btn_update_prices = AnimatedButton(" Fiyatlari Guncelle")
        self.btn_update_prices.setIconName("refresh-cw", color="@COLOR_TEXT_PRIMARY")
        self.btn_update_prices.clicked.connect(self._actions.on_update_prices)

        self.lbl_last_update = QLabel("")
        self.lbl_last_update.setProperty("cssClass", "lastUpdateLabel")

        self.btn_capital = AnimatedButton(" Sermaye Yonetimi")
        self.btn_capital.setIconName("coins", color="@COLOR_TEXT_PRIMARY")
        self.btn_capital.clicked.connect(self._actions.on_capital_management)
        self.btn_capital.setProperty("cssClass", "secondaryButton")

        self.btn_backfill = AnimatedButton(" Gecmis Veri Yonetimi")
        self.btn_backfill.setIconName("history", color="@COLOR_TEXT_PRIMARY")
        self.btn_backfill.clicked.connect(self._actions.on_backfill)
        self.btn_backfill.setProperty("cssClass", "secondaryButton")

        self.btn_export_today = AnimatedButton(" Rapor: Bugun")
        self.btn_export_today.setIconName("file-text", color="@COLOR_TEXT_PRIMARY")
        self.btn_export_today.clicked.connect(self._actions.on_export_today)

        self.btn_export_range = AnimatedButton(" Rapor: Tarih Araligi")
        self.btn_export_range.setIconName("file-text", color="@COLOR_TEXT_PRIMARY")
        self.btn_export_range.clicked.connect(self._actions.on_export_range)

        top_layout.addWidget(self.btn_new_trade)
        top_layout.addWidget(self.btn_update_prices)
        top_layout.addWidget(self.btn_capital)
        top_layout.addWidget(self.btn_backfill)
        top_layout.addWidget(self.btn_export_today)
        top_layout.addWidget(self.btn_export_range)
        top_layout.addStretch()
        actions_layout.addLayout(top_layout)

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
        self.main_layout.addWidget(self.portfolio_table_widget)

    def on_page_enter(self):
        self._presenter.load_capital()
        self.refresh_data()
        self._sync_last_update_label()
        QTimer.singleShot(0, self.show_last_update_toast_once)

    def refresh_data(self):
        self._presenter.refresh_data()

    def record_last_update_time(self, updated_at=None):
        from datetime import datetime

        updated_at = updated_at or datetime.now()
        value = updated_at.isoformat(timespec="seconds")
        self._settings.setValue(LAST_UPDATE_SETTINGS_KEY, value)
        self._settings.sync()
        self._last_update_toast_shown_for = None
        self._sync_last_update_label(updated_at)
        return updated_at

    def show_last_update_toast_once(self, force: bool = False, detail: str | None = None) -> None:
        updated_at = self._get_last_update_time()
        if updated_at is None:
            return

        value = updated_at.isoformat(timespec="seconds")
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

    def _get_last_update_time(self):
        from datetime import datetime

        value = self._settings.value(LAST_UPDATE_SETTINGS_KEY, "", type=str)
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _format_last_update_message(updated_at) -> str:
        return f"Son guncelleme: {updated_at.strftime('%d.%m.%Y %H:%M')} (15dk gecikmeli)"

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
