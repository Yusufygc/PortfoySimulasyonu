from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

logger = logging.getLogger(__name__)

from PyQt5.QtCore import QSettings, QThreadPool, QTimer, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.navigation.page_factory import PageFactory
from src.ui.widgets.shared import AnimatedButton
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker


AUTO_BACKFILL_SETTINGS_KEY = "settings/last_auto_price_backfill_at"


class MainWindow(QMainWindow):
    PAGE_DASHBOARD = 0
    PAGE_WATCHLIST = 1
    PAGE_MODEL_PORTFOLIO = 2
    PAGE_ANALYSIS = 3
    PAGE_COMPARISON = 4
    PAGE_STOCK_DETAIL = 5
    PAGE_OPTIMIZATION = 6
    PAGE_PLANNING = 7
    PAGE_RISK_PROFILE = 8
    PAGE_AI_PAGE = 9
    PAGE_SETTINGS = 10
    PAGE_COUNT = 11

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.navigation_history: List[int] = []
        self._price_lookup = container.price_lookup_service.lookup_price_for_ticker
        self._page_factory = PageFactory(
            container=container,
            price_lookup_func=self._price_lookup,
            parent_window=self,
        )
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._threadpool = QThreadPool()
        self.setWindowTitle("Portföy Simülasyonu")
        self.setWindowIcon(QIcon("icons/portfoy-simulasyonu.ico"))
        self.resize(1300, 800)

        self._init_ui()
        self._goto_page(self.PAGE_DASHBOARD)
        QTimer.singleShot(0, self._start_auto_price_backfill_once)

    def _init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 25, 15, 25)
        self.sidebar_layout.setSpacing(10)

        lbl_app_title = QLabel("Portföy\nSimülasyonu")
        lbl_app_title.setProperty("cssClass", "appTitle")
        lbl_app_title.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(lbl_app_title)

        self._add_separator()

        self.btn_dashboard = self._create_nav_button("Dashboard", self.PAGE_DASHBOARD, "layout-dashboard")
        self.btn_watchlist = self._create_nav_button("Listelerim", self.PAGE_WATCHLIST, "list")
        self.btn_model_portfolio = self._create_nav_button("Model Portföyler", self.PAGE_MODEL_PORTFOLIO, "wallet")
        self.btn_analysis = self._create_nav_button("Analiz", self.PAGE_ANALYSIS, "trending-up")
        self.btn_comparison = self._create_nav_button("Karşılaştırma", self.PAGE_COMPARISON, "bar-chart-2")
        self.btn_optimization = self._create_nav_button("Optimizasyon", self.PAGE_OPTIMIZATION, "zap")
        self.btn_planning = self._create_nav_button("Finansal Planlama", self.PAGE_PLANNING, "save")
        self.btn_risk_profile = self._create_nav_button("Risk Profili", self.PAGE_RISK_PROFILE, "shield-check")
        self.btn_ai_page = self._create_nav_button("AI Asistan", self.PAGE_AI_PAGE, "bot")
        self.btn_settings = self._create_nav_button("Ayarlar", self.PAGE_SETTINGS, "save")
 
        for button in (
            self.btn_dashboard,
            self.btn_watchlist,
            self.btn_model_portfolio,
            self.btn_analysis,
            self.btn_comparison,
            self.btn_optimization,
            self.btn_planning,
            self.btn_risk_profile,
            self.btn_ai_page,
            self.btn_settings,
        ):
            self.sidebar_layout.addWidget(button)

        self.sidebar_layout.addStretch()
        self._add_separator()


        self.stacked_widget = QStackedWidget()
        self.pages = {}
        for _ in range(self.PAGE_COUNT):
            self.stacked_widget.addWidget(QWidget())

        self._instantiate_page(self.PAGE_DASHBOARD)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stacked_widget, 1)

    def _create_nav_button(self, text: str, page_index: int, icon_name: str = "") -> AnimatedButton:
        button = AnimatedButton(f" {text}")
        if icon_name:
            button.setIconName(icon_name, color="@COLOR_TEXT_SECONDARY")
        button.setCheckable(True)
        button.clicked.connect(lambda: self._goto_page(page_index))
        button.setProperty("cssClass", "navMenuBtn")
        return button

    def _add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setProperty("cssClass", "navSeparator")
        self.sidebar_layout.addWidget(line)

    def _instantiate_page(self, page_index: int):
        if page_index in self.pages:
            return

        page = self._page_factory.create(page_index)
        if page is None:
            logger.error("PageFactory returned None for page_index=%d", page_index)
            Toast.error(self, "Sayfa yüklenemedi. Uygulama durumu kontrol edin.")
            return

        if hasattr(page, "navigate_back"):
            page.navigate_back.connect(self._on_back)

        placeholder = self.stacked_widget.widget(page_index)
        self.stacked_widget.removeWidget(placeholder)
        self.stacked_widget.insertWidget(page_index, page)
        self.pages[page_index] = page

    def _goto_page(self, page_index: int):
        current_index = self.stacked_widget.currentIndex()
        if current_index == page_index and current_index in self.pages:
            return

        if current_index in self.pages:
            current_page = self.pages[current_index]
            if hasattr(current_page, "on_page_leave"):
                current_page.on_page_leave()

        if page_index not in self.pages:
            self._instantiate_page(page_index)
        if page_index not in self.pages:
            return

        if current_index != page_index and current_index >= 0:
            self.navigation_history.append(current_index)

        self._activate_page(page_index)

    def _activate_page(self, page_index: int):
        self.stacked_widget.setCurrentIndex(page_index)
        new_page = self.stacked_widget.currentWidget()
        if hasattr(new_page, "on_page_enter"):
            new_page.on_page_enter()
        self._update_nav_buttons(page_index)

    def show_stock_detail(self, ticker: str, stock_id: Optional[int] = None, context: Optional[dict] = None):
        if self.PAGE_STOCK_DETAIL not in self.pages:
            self._instantiate_page(self.PAGE_STOCK_DETAIL)
        page = self.pages[self.PAGE_STOCK_DETAIL]
        page.set_stock(ticker, stock_id, context=context)
        self._goto_page(self.PAGE_STOCK_DETAIL)

    def show_dashboard(self):
        self._goto_page(self.PAGE_DASHBOARD)

    def show_model_portfolios(self):
        self._goto_page(self.PAGE_MODEL_PORTFOLIO)

    def _on_back(self):
        if not self.navigation_history:
            return

        current_index = self.stacked_widget.currentIndex()
        if current_index in self.pages:
            current_page = self.pages[current_index]
            if hasattr(current_page, "on_page_leave"):
                current_page.on_page_leave()

        previous_page_idx = self.navigation_history.pop()
        if previous_page_idx not in self.pages:
            self._instantiate_page(previous_page_idx)
        if previous_page_idx in self.pages:
            self._activate_page(previous_page_idx)

    def _update_nav_buttons(self, active_page: int):
        nav_buttons = {
            self.PAGE_DASHBOARD: (self.btn_dashboard, "layout-dashboard"),
            self.PAGE_WATCHLIST: (self.btn_watchlist, "list"),
            self.PAGE_MODEL_PORTFOLIO: (self.btn_model_portfolio, "wallet"),
            self.PAGE_ANALYSIS: (self.btn_analysis, "trending-up"),
            self.PAGE_COMPARISON: (self.btn_comparison, "bar-chart-2"),
            self.PAGE_OPTIMIZATION: (self.btn_optimization, "zap"),
            self.PAGE_PLANNING: (self.btn_planning, "save"),
            self.PAGE_RISK_PROFILE: (self.btn_risk_profile, "shield-check"),
            self.PAGE_AI_PAGE: (self.btn_ai_page, "bot"),
            self.PAGE_SETTINGS: (self.btn_settings, "save"),
        }

        for page_idx, (btn, icon_name) in nav_buttons.items():
            is_active = (page_idx == active_page)
            btn.setChecked(is_active)
            color = "@COLOR_TEXT_WHITE" if is_active else "@COLOR_TEXT_SECONDARY"
            btn.setIconName(icon_name, color=color)

    def _start_auto_price_backfill_once(self) -> None:
        service = getattr(self.container, "price_data_health_service", None)
        if service is None:
            return
        today = date.today()
        last_run = self._settings.value(AUTO_BACKFILL_SETTINGS_KEY, "", type=str)
        if last_run == today.isoformat():
            return

        worker = Worker(service.update_from_latest_to_today, today)
        worker.signals.result.connect(self._on_auto_price_backfill_success)
        worker.signals.error.connect(self._on_auto_price_backfill_error)
        self._threadpool.start(worker)

    def _on_auto_price_backfill_success(self, result) -> None:
        self._settings.setValue(AUTO_BACKFILL_SETTINGS_KEY, date.today().isoformat())
        self._settings.sync()
        if getattr(result, "prices", None) and getattr(self.container, "event_bus", None):
            self.container.event_bus.prices_updated.emit(result.prices)
        updated_count = getattr(result, "updated_count", 0)
        error_count = len(getattr(result, "errors", []) or [])
        if updated_count > 0:
            Toast.success(self, f"Otomatik veri güncelleme tamamlandı: {updated_count} fiyat kaydı eklendi.")
        elif error_count:
            Toast.warning(self, f"Otomatik veri güncelleme tamamlandı, {error_count} hata oluştu.")

    def _on_auto_price_backfill_error(self, err_tuple) -> None:
        self._settings.setValue(AUTO_BACKFILL_SETTINGS_KEY, date.today().isoformat())
        self._settings.sync()
        Toast.warning(self, f"Otomatik veri güncelleme çalıştırılamadı: {err_tuple[1]}")
