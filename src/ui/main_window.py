from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import os
import logging
from datetime import date, datetime, time as dt_time, timedelta
from typing import List, Optional

from src.qt_compat.qtcore import QSettings, QThreadPool, QTimer, Qt, QPropertyAnimation, QEasingCurve, QSize
from src.qt_compat.qtgui import QIcon
from src.qt_compat.qtwidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.navigation.page_factory import PageFactory
from src.ui.pages.model_portfolio.utils.portfolio_price_event_persister import ModelPortfolioPriceEventPersister
from src.ui.shared.live_price_refresh_controller import LivePriceRefreshController
from src.ui.shared.price_event_publisher import publish_prices_updated
from src.ui.widgets.shared import AnimatedButton, Toast
from src.ui.worker import Worker


logger = logging.getLogger(__name__)

AUTO_BACKFILL_SETTINGS_KEY = "settings/last_auto_price_backfill_at"
AUTO_BIST_BACKFILL_SETTINGS_KEY = "settings/last_auto_bist_backfill_at"
AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY = "settings/last_auto_corporate_action_discovery_at"
AUTO_TECHNICAL_SCAN_SETTINGS_KEY = "settings/last_auto_technical_scan_at"
BIST_MARKET_CLOSE_TIME = dt_time(18, 30)  # BIST kapanış sonrası fiyat verisi hazır
MAIN_WINDOW_INITIAL_WIDTH = 1600
MAIN_WINDOW_INITIAL_HEIGHT = 900


class _WrapNavButton(AnimatedButton):
    """Uzun sidebar metni için otomatik word-wrap: sizeHint yüksekliği metne göre ayarlanır."""

    _AVAILABLE_TEXT_W = 145  # sidebar(220) − paddingLR(30) − icon(18) − gap(6) − margin(~21)

    def sizeHint(self) -> QSize:
        sh  = super().sizeHint()
        txt = self.text().strip()
        if "\n" not in txt:
            return sh
        fm  = self.fontMetrics()
        r   = fm.boundingRect(0, 0, self._AVAILABLE_TEXT_W, 9999,
                               int(Qt.TextWordWrap | Qt.AlignLeft), txt)
        return QSize(sh.width(), max(sh.height(), r.height() + 18))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()


def _split_nav_text(text: str, max_chars: int = 16) -> str:
    """Metin max_chars'tan uzunsa en iyi boşluk noktasında \\n ekle."""
    if len(text) <= max_chars:
        return text
    mid   = len(text) // 2
    left  = text.rfind(" ", 0, mid + 1)
    right = text.find(" ", mid)
    if left == -1 and right == -1:
        return text
    if left == -1:
        split = right
    elif right == -1:
        split = left
    else:
        split = left if abs(left - mid) <= abs(right - mid) else right
    return text[:split] + "\n" + text[split + 1:]


def _make_nav_button(text: str, page_index: int, icon_name: str, goto_page_func) -> "_WrapNavButton":
    display = _split_nav_text(text)
    button  = _WrapNavButton(f" {display}")
    if icon_name:
        button.setIconName(icon_name, color="@COLOR_TEXT_SECONDARY")
    button.setCheckable(True)
    button.clicked.connect(lambda: goto_page_func(page_index))
    button.setProperty("cssClass", "navMenuBtn")
    return button


def _add_nav_separator(sidebar_layout) -> None:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setProperty("cssClass", "navSeparator")
    sidebar_layout.addWidget(line)


def _build_sidebar_nav(sidebar_layout, goto_page_func):
    # Page indices match MainWindow.PAGE_* constants
    _add_nav_separator(sidebar_layout)
    btn_dashboard      = _make_nav_button(L10N.DASHBOARD,        0,  "layout-dashboard", goto_page_func)
    btn_watchlist      = _make_nav_button(L10N.LISTELERIM,        1,  "list",             goto_page_func)
    btn_model_port     = _make_nav_button(L10N.MODEL_PORTFOYLER,  2,  "wallet",           goto_page_func)
    btn_analysis       = _make_nav_button(L10N.ANALIZ,            3,  "trending-up",      goto_page_func)
    btn_comparison     = _make_nav_button(L10N.KARSILASTIRMA,     4,  L10N.BARCHART2,     goto_page_func)
    btn_optimization   = _make_nav_button(L10N.OPTIMIZASYON,      6,  "zap",              goto_page_func)
    btn_planning       = _make_nav_button(L10N.FINANSAL_PLANLAMA, 7,  "save",             goto_page_func)
    btn_risk_profile   = _make_nav_button(L10N.RISK_PROFILI,      8,  "shield-check",     goto_page_func)
    btn_ai_page        = _make_nav_button(L10N.AI_ASISTAN,             9,  "bot",          goto_page_func)
    btn_settings       = _make_nav_button(L10N.SETTINGS,               10, "save",         goto_page_func)
    btn_financials     = _make_nav_button(L10N.BILANCO_VE_FINANSALLAR, 11, "bar-chart-2",  goto_page_func)
    btn_shareholders   = _make_nav_button(L10N.ORTAKLIK_YAPISI,        12, "users",        goto_page_func)
    btn_technical      = _make_nav_button(L10N.TEKNIK_ANALIZ,           13, "activity",     goto_page_func)
    for btn in (btn_dashboard, btn_watchlist, btn_model_port, btn_financials, btn_shareholders,
                btn_technical, btn_analysis, btn_comparison, btn_optimization, btn_planning,
                btn_risk_profile, btn_ai_page, btn_settings):
        sidebar_layout.addWidget(btn)
    sidebar_layout.addStretch()
    _add_nav_separator(sidebar_layout)
    return (btn_dashboard, btn_watchlist, btn_model_port, btn_analysis, btn_comparison,
            btn_optimization, btn_planning, btn_risk_profile, btn_ai_page, btn_settings,
            btn_financials, btn_shareholders, btn_technical)


def last_completed_trading_day(today: date, trading_calendar) -> date:
    candidate = today - timedelta(days=1)
    while trading_calendar is not None and not trading_calendar.is_trading_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def fade_in_page(page: QWidget | None) -> None:
    """Sayfa geçişlerinde kararma ve kapanıp-açılma hissiyatını engellemek için direkt geçiş yapılır."""
    return



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
    PAGE_FINANCIALS = 11
    PAGE_SHAREHOLDERS = 12
    PAGE_TECHNICAL = 13
    PAGE_COUNT = 14

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
        self._live_price_refresh_controller = LivePriceRefreshController(
            parent=self,
            container=container,
            settings=self._settings,
            threadpool=self._threadpool,
        )
        self._auto_price_backfill_target_date = None
        self._connect_model_portfolio_price_persister()
        env = os.getenv("PORTFOYSIM_ENV", "").upper()
        self.setWindowTitle(f"{L10N.APP_TITLE} [{env} ORTAMI]" if env else L10N.APP_TITLE)
        self.setWindowIcon(QIcon("icons/icon.ico"))
        self.resize(MAIN_WINDOW_INITIAL_WIDTH, MAIN_WINDOW_INITIAL_HEIGHT)

        self._init_ui()
        self._goto_page(self.PAGE_DASHBOARD)
        QTimer.singleShot(0, self._start_auto_price_backfill_once)
        QTimer.singleShot(0, self._start_auto_bist_backfill_once)
        self._live_price_refresh_controller.start()
        QTimer.singleShot(0, self._start_auto_corporate_action_discovery_once)
        QTimer.singleShot(0, self._start_auto_technical_scan_once)

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
        lbl_app_title = QLabel(L10N.SIDEBAR_PORTFOY_SIMULASYONU)
        lbl_app_title.setProperty("cssClass", "appTitle")
        lbl_app_title.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(lbl_app_title)
        env = os.getenv("PORTFOYSIM_ENV", "").upper()
        if env:
            lbl = QLabel(f"{env} ORTAMI")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color:#FF9800;font-weight:bold;background-color:#3E2723;border:1px solid #FF9800;border-radius:4px;padding:4px;margin:5px 0;")
            self.sidebar_layout.addWidget(lbl)
        (self.btn_dashboard, self.btn_watchlist, self.btn_model_portfolio,
         self.btn_analysis, self.btn_comparison, self.btn_optimization,
         self.btn_planning, self.btn_risk_profile, self.btn_ai_page,
         self.btn_settings, self.btn_financials,
         self.btn_shareholders, self.btn_technical) = _build_sidebar_nav(self.sidebar_layout, self._goto_page)
        self.stacked_widget = QStackedWidget()
        self.pages = {}
        for _ in range(self.PAGE_COUNT):
            self.stacked_widget.addWidget(QWidget())
        self._instantiate_page(self.PAGE_DASHBOARD)
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stacked_widget, 1)

    def _connect_model_portfolio_price_persister(self) -> None:
        event_bus = getattr(self.container, "event_bus", None)
        service = getattr(self.container, "model_portfolio_service", None)
        if event_bus is None or service is None:
            return
        self._model_portfolio_price_event_persister = ModelPortfolioPriceEventPersister(service)
        event_bus.prices_updated.connect(self._model_portfolio_price_event_persister.on_prices_updated)

    def _instantiate_page(self, page_index: int):
        if page_index in self.pages:
            return

        page = self._page_factory.create(page_index)
        if page is None:
            logger.error("PageFactory returned None for page_index=%d", page_index)
            Toast.error(self, L10N.SAYFA_YUKLENEMEDI_UYGULAMA_DURUMU_KONTROL)
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
        new_page = self.stacked_widget.widget(page_index)
        fade_in_page(new_page)
        self.stacked_widget.setCurrentIndex(page_index)
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
            self.PAGE_COMPARISON: (self.btn_comparison, L10N.BARCHART2),
            self.PAGE_OPTIMIZATION: (self.btn_optimization, "zap"),
            self.PAGE_PLANNING: (self.btn_planning, "save"),
            self.PAGE_RISK_PROFILE: (self.btn_risk_profile, "shield-check"),
            self.PAGE_AI_PAGE: (self.btn_ai_page, "bot"),
            self.PAGE_SETTINGS: (self.btn_settings, "save"),
            self.PAGE_FINANCIALS: (self.btn_financials, "bar-chart-2"),
            self.PAGE_SHAREHOLDERS: (self.btn_shareholders, "users"),
            self.PAGE_TECHNICAL: (self.btn_technical, "activity"),
        }

        for page_idx, (btn, icon_name) in nav_buttons.items():
            is_active = page_idx == active_page
            btn.setChecked(is_active)
            color = "@COLOR_TEXT_WHITE" if is_active else "@COLOR_TEXT_SECONDARY"
            btn.setIconName(icon_name, color=color)

    def _start_auto_price_backfill_once(self) -> None:
        service = getattr(self.container, "price_data_health_service", None)
        if service is None:
            return
        target_date = last_completed_trading_day(
            date.today(),
            getattr(self.container, "trading_calendar", None),
        )
        last_run = self._settings.value(AUTO_BACKFILL_SETTINGS_KEY, "", type=str)
        if last_run == target_date.isoformat():
            return

        self._auto_price_backfill_target_date = target_date
        worker = Worker(service.update_from_latest_to_today, target_date)
        worker.signals.result.connect(self._on_auto_price_backfill_success)
        worker.signals.error.connect(self._on_auto_price_backfill_error)
        self._threadpool.start(worker)

    def _on_auto_price_backfill_success(self, result) -> None:
        target_date = self._auto_price_backfill_target_date or last_completed_trading_day(
            date.today(),
            getattr(self.container, "trading_calendar", None),
        )
        self._settings.setValue(AUTO_BACKFILL_SETTINGS_KEY, target_date.isoformat())
        self._settings.sync()
        publish_prices_updated(getattr(self.container, "event_bus", None), getattr(result, "prices", None))
        updated_count = getattr(result, "updated_count", 0)
        error_count = len(getattr(result, "errors", []) or [])
        if updated_count > 0:
            Toast.success(self, L10N.OTOMATIK_VERI_GUNCELLEME_TAMAMLANDI_TMPL.format(count=updated_count))
        elif error_count:
            Toast.warning(self, L10N.OTOMATIK_VERI_GUNCELLEME_HATA_TMPL.format(count=error_count))

    def _on_auto_price_backfill_error(self, err_tuple) -> None:
        Toast.warning(self, L10N.OTOMATIK_VERI_GUNCELLEME_CALISTIRILAMADI_TMPL.format(exc=err_tuple[1]))

    # ------------------------------------------------------------------
    # Phase A2: tüm BIST için otomatik veri tamamlama (18:30 sonrası)
    # ------------------------------------------------------------------

    def _start_auto_bist_backfill_once(self) -> None:
        """Açılışta tüm BIST tickerleri için eksik kapanışları yfinance ile doldur.

        Şart: saat ≥ 18:30 (piyasa kapandı) ve aynı işlem günü için zaten çalışmadıysa.
        "Açmayı unuttum" senaryosu: latest_date + 1 → today aralığı otomatik dolar
        (PriceDataHealthService.update_from_latest_to_today davranışı).
        """
        from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_BIST
        service = getattr(self.container, "price_data_health_service", None)
        if service is None:
            return
        if datetime.now().time() < BIST_MARKET_CLOSE_TIME:
            logger.info("BIST backfill atlandı (saat < 18:30, piyasa açık olabilir)")
            return
        target_date = last_completed_trading_day(
            date.today(),
            getattr(self.container, "trading_calendar", None),
        )
        last_run = self._settings.value(AUTO_BIST_BACKFILL_SETTINGS_KEY, "", type=str)
        if last_run == target_date.isoformat():
            return

        self._auto_bist_backfill_target_date = target_date
        worker = Worker(service.update_from_latest_to_today, target_date, PRICE_SCOPE_ALL_BIST)
        worker.signals.result.connect(self._on_auto_bist_backfill_success)
        worker.signals.error.connect(self._on_auto_bist_backfill_error)
        self._threadpool.start(worker)

    def _on_auto_bist_backfill_success(self, result) -> None:
        target_date = getattr(self, "_auto_bist_backfill_target_date", None) or last_completed_trading_day(
            date.today(),
            getattr(self.container, "trading_calendar", None),
        )
        self._settings.setValue(AUTO_BIST_BACKFILL_SETTINGS_KEY, target_date.isoformat())
        self._settings.sync()
        publish_prices_updated(getattr(self.container, "event_bus", None), getattr(result, "prices", None))
        updated_count = getattr(result, "updated_count", 0)
        error_count = len(getattr(result, "errors", []) or [])
        if updated_count > 0:
            Toast.success(self, L10N.OTOMATIK_BIST_GUNCELLEME_TAMAMLANDI_TMPL.format(count=updated_count))
        elif error_count:
            Toast.warning(self, L10N.OTOMATIK_BIST_GUNCELLEME_HATA_TMPL.format(count=error_count))

    def _on_auto_bist_backfill_error(self, err_tuple) -> None:
        Toast.warning(self, L10N.OTOMATIK_BIST_GUNCELLEME_CALISTIRILAMADI_TMPL.format(exc=err_tuple[1]))

    def reload_live_price_refresh_settings(self) -> None:
        self._live_price_refresh_controller.reload_settings()

    def _start_auto_corporate_action_discovery_once(self) -> None:
        service = getattr(self.container, "corporate_action_discovery_service", None)
        if service is None:
            return
        today = date.today()
        last_run = self._settings.value(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, "", type=str)
        if last_run == today.isoformat():
            return

        worker = Worker(service.discover)
        worker.signals.result.connect(self._on_auto_corporate_action_discovery_success)
        worker.signals.error.connect(self._on_auto_corporate_action_discovery_error)
        self._threadpool.start(worker)

    def _on_auto_corporate_action_discovery_success(self, result) -> None:
        self._settings.setValue(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, date.today().isoformat())
        self._settings.sync()
        saved_count = getattr(result, "saved_count", 0)
        if saved_count > 0:
            Toast.success(self, L10N.KURUMSAL_AKSIYON_ADAYLARI_BULUNDU_TMPL.format(count=saved_count))

    def _on_auto_corporate_action_discovery_error(self, err_tuple) -> None:
        self._settings.setValue(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, date.today().isoformat())
        self._settings.sync()
        logger.warning("Auto corporate action discovery failed: %s", err_tuple[1])

    def _start_auto_technical_scan_once(self) -> None:
        """Açılışta son taramadan beri 24 saatten fazla geçmişse otomatik scan çalıştır."""
        service = getattr(self.container, "technical_analysis_service", None)
        if service is None:
            return

        last_scan_str = self._settings.value(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, "", type=str)
        needs_scan = False
        if not last_scan_str:
            needs_scan = True
        else:
            try:
                last_scan_dt = datetime.fromisoformat(last_scan_str)
                if datetime.now() - last_scan_dt > timedelta(hours=24):
                    needs_scan = True
            except Exception:
                needs_scan = True

        if not needs_scan:
            logger.info("Otomatik teknik analiz taraması atlandı (son tarama <24h önce)")
            return

        logger.info("Otomatik teknik analiz taraması başlatılıyor...")
        worker = Worker(service.scan_all)
        worker.signals.result.connect(self._on_auto_technical_scan_success)
        worker.signals.error.connect(self._on_auto_technical_scan_error)
        self._threadpool.start(worker)

    def _on_auto_technical_scan_success(self, result) -> None:
        self._settings.setValue(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, datetime.now().isoformat())
        self._settings.sync()
        
        # Eğer aktif sayfa teknik analiz ise yenile
        current_page = self.stacked_widget.currentWidget()
        if hasattr(current_page, "_on_refresh_recent"):
            current_page._on_refresh_recent()

        Toast.success(self, L10N.TARAMA_TAMAMLANDI_TMPL.format(
            scanned=result.scanned_count,
            new=result.new_event_count,
            skipped=result.skipped_count,
        ))

    def _on_auto_technical_scan_error(self, err_tuple) -> None:
        logger.error("Otomatik teknik analiz tarama hatası: %s", err_tuple[1])
        Toast.warning(self, L10N.TARAMA_HATA_TMPL.format(exc=err_tuple[1]))
