from src.ui.shared.locale_tr import L10N
from src.ui.shared.locale_tr import L10N
import logging
from decimal import Decimal

from PyQt5.QtCore import QModelIndex, QSettings, QThreadPool, QTimer, QSize
from PyQt5.QtWidgets import QAction, QHBoxLayout, QLabel, QMenu, QVBoxLayout

from src.ui.pages.base_page import BasePage
from src.ui.shared.last_update_mixin import LastUpdateDisplayMixin
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.dashboard import CapitalDialog, DateRangeDialog, NewStockTradeDialog
from src.ui.widgets.shared import AnimatedButton

from .dashboard_actions import DashboardActions
from .dashboard_portfolio_table import DashboardPortfolioTable
from .dashboard_presenter import DashboardPresenter
from .dashboard_summary_cards import DashboardSummaryCards

logger = logging.getLogger(__name__)

LAST_UPDATE_SETTINGS_KEY    = "dashboard/last_price_update_at"
WEEKLY_RETURN_SETTINGS_KEY  = "dashboard/weekly_return_pct"
MONTHLY_RETURN_SETTINGS_KEY = "dashboard/monthly_return_pct"


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
        if row < 0 or row >= self.portfolio_model.rowCount():
            return

        position = self.portfolio_model.get_position(row)
        stock = self.stock_repo.get_stock_by_id(position.stock_id)
        ticker = stock.ticker if stock else None

        main_window = self.window()
        if hasattr(main_window, "show_stock_detail"):
            main_window.show_stock_detail(ticker, position.stock_id)
