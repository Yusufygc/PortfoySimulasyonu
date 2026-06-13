from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from datetime import date, timedelta

from src.qt_compat.qtcore import QSize, Qt, QThreadPool
from src.qt_compat.qtwidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.application.services.analysis import AnalysisFilterState
from src.ui.pages.base_page import BasePage
from src.ui.widgets.shared.controls.icon_label import IconLabel
from src.ui.widgets.shared.controls.animated_button import AnimatedButton
from src.ui.worker import Worker

from .analysis_control_panel import AnalysisControlPanel
from .analysis_overview_section import AnalysisOverviewSection
from .analysis_risk_section import AnalysisRiskSection

logger = logging.getLogger(__name__)


class AnalysisPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.ANALIZ
        self.analysis_service = container.analysis_service
        self.threadpool = QThreadPool()
        self._request_seq = 0
        self._active_request_id = None
        self._active_worker = None
        self._init_ui()

    def _init_ui(self) -> None:
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        left_container = QWidget()
        left_container.setMinimumWidth(0)
        left_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        icon_lbl = IconLabel("line-chart", color="@COLOR_ACCENT", size=28)
        header_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        lbl_title = QLabel(L10N.ANALIZ_VE_KARSILASTIRMA)
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel(L10N.PORTFOY_BENCHMARK_RISK_TEK_AKIS)
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.btn_toggle_panel = AnimatedButton(L10N.FILTRELERI_GIZLE)
        self.btn_toggle_panel.setProperty("cssClass", "secondaryButton")
        self.btn_toggle_panel.setIconName("layers", color="@COLOR_TEXT_SECONDARY", size=18)
        self.btn_toggle_panel.clicked.connect(self._toggle_control_panel)
        header_layout.addWidget(self.btn_toggle_panel)

        self.btn_refresh = AnimatedButton(L10N.ANALIZI_YENILE)
        self.btn_refresh.setProperty("cssClass", "primaryButton")
        self.btn_refresh.setIconName("refresh-cw", color="@COLOR_TEXT_WHITE", size=18)
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)
        left_layout.addLayout(header_layout)

        self.warning_banner = QLabel("")
        self.warning_banner.setProperty("cssClass", "warningBanner")
        self.warning_banner.setWordWrap(True)
        self.warning_banner.hide()
        left_layout.addWidget(self.warning_banner)

        self.tabs = QTabWidget()
        self.tabs.setProperty("cssClass", "mainTabWidget")
        self.tabs.setMinimumWidth(0)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tab_bar = self.tabs.tabBar()
        tab_bar.setExpanding(True)
        tab_bar.setUsesScrollButtons(False)
        tab_bar.setElideMode(Qt.ElideNone)

        self.overview_section = AnalysisOverviewSection()
        self.risk_section = AnalysisRiskSection()
        self.tabs.addTab(self._wrap_scroll(self.overview_section), L10N.GENEL_BAKIS)
        self.tabs.addTab(self._wrap_scroll(self.risk_section), L10N.DAGILIM_VE_RISK)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        left_layout.addWidget(self.tabs, 1)
        content_layout.addWidget(left_container, 1)

        self.control_panel = AnalysisControlPanel()
        self.control_panel.filter_changed.connect(self._request_refresh)
        self.control_panel.source_changed.connect(self._on_source_changed)

        PANEL_WIDTH = 420

        self.control_panel_scroll = QScrollArea()
        self.control_panel_scroll.setWidgetResizable(True)
        self.control_panel_scroll.setFrameShape(QFrame.NoFrame)
        self.control_panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.control_panel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.control_panel_scroll.setFixedWidth(PANEL_WIDTH)
        self.control_panel_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.control_panel_scroll.setWidget(self.control_panel)

        self.control_panel_column = QWidget()
        self.control_panel_column.setFixedWidth(PANEL_WIDTH)
        self.control_panel_column.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        panel_layout = QVBoxLayout(self.control_panel_column)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        panel_layout.addWidget(self.control_panel_scroll, 1)

        content_layout.addWidget(self.control_panel_column, 0)

        self.main_layout.addLayout(content_layout, 1)

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(0)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        content = QWidget()
        content.setObjectName("scroll_content")
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        widget.setMinimumWidth(0)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(widget)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _toggle_control_panel(self):
        is_visible = self.control_panel_column.isVisible()
        self.control_panel_column.setVisible(not is_visible)
        if is_visible:
            self.btn_toggle_panel.setText(L10N.FILTRELERI_GOSTER)
        else:
            self.btn_toggle_panel.setText(L10N.FILTRELERI_GIZLE)

    def on_page_enter(self):
        self.control_panel.blockSignals(True)
        self._load_static_options()
        self._sync_source_context()
        if getattr(self, '_is_first_load', True):
            self.control_panel.reset_to_earliest_date()
            self._is_first_load = False
        self.control_panel.blockSignals(False)
        self._request_refresh()

    def refresh_data(self):
        self._load_static_options()
        self._sync_source_context()
        self._request_refresh()

    def _load_static_options(self) -> None:
        options = self.analysis_service.get_portfolio_options()
        self.control_panel.set_portfolio_options(options)
        self.control_panel.set_benchmarks(self.analysis_service.get_benchmark_definitions())

    def _sync_source_context(self) -> None:
        source = self.control_panel.selected_portfolio_source() or "dashboard"
        self.control_panel.set_stocks(self.analysis_service.get_stock_map_for_source(source))
        earliest = self.analysis_service.get_first_trade_date_for_source(source) or (date.today() - timedelta(days=365))
        self.control_panel.set_earliest_date(earliest)

    def _on_source_changed(self, _source: str) -> None:
        self._sync_source_context()
        self.control_panel.reset_to_earliest_date()

    def _build_filter_state(self) -> AnalysisFilterState:
        start_date, end_date = self.control_panel.date_range()
        return AnalysisFilterState(
            start_date=start_date,
            end_date=end_date,
            selected_stock_ids=self.control_panel.selected_stock_ids(),
            selected_benchmarks=self.control_panel.selected_benchmarks(),
            portfolio_source=self.control_panel.selected_portfolio_source() or "dashboard",
            comparison_portfolio_sources=[],
            currency_mode=self.control_panel.selected_currency_mode(),
        )

    def _request_refresh(self) -> None:
        filter_state = self._build_filter_state()
        self._request_seq += 1
        request_id = self._request_seq
        self._active_request_id = request_id

        if filter_state.start_date > filter_state.end_date:
            self._render_error("Ba\u015flang\u0131\u00e7 tarihi biti\u015f tarihinden sonra olamaz.")
            self._complete_request(request_id)
            return

        self._set_loading(True)

        payload_loader = getattr(self.analysis_service, "get_overview_risk_payload", None)
        if payload_loader is None:
            payload_loader = self.analysis_service.get_page_payload
        worker = Worker(payload_loader, filter_state)
        worker.signals.result.connect(lambda result, rid=request_id: self._on_payload_ready(rid, result))
        worker.signals.error.connect(lambda err, rid=request_id: self._on_payload_error(rid, err))
        worker.signals.finished.connect(lambda rid=request_id: self._on_payload_finished(rid))
        self._active_worker = worker
        self.threadpool.start(worker)

    def _on_payload_ready(self, request_id: int, payload: dict) -> None:
        if request_id != self._request_seq:
            return
        self.warning_banner.hide()
        self.overview_section.set_data(payload["overview"])
        self.risk_section.set_data(payload["risk"])
        if self.tabs.currentIndex() == 1:
            self.risk_section.activate_charts()
        self._complete_request(request_id)

    def _on_payload_error(self, request_id: int, err_tuple) -> None:
        if request_id != self._request_seq:
            return
        logger.error("Analiz y\u00fcklenemedi: %s", err_tuple[1], exc_info=True)
        self._render_error(str(err_tuple[1]))
        self._complete_request(request_id)

    def _on_payload_finished(self, request_id: int) -> None:
        if request_id != self._request_seq:
            return
        self._active_worker = None
        self._complete_request(request_id)

    def _complete_request(self, request_id: int) -> None:
        if request_id != self._request_seq:
            return
        self._active_request_id = None
        self._set_loading(False)

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            self.risk_section.activate_charts()

    def _render_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.overview_section.set_error(message)
        self.risk_section.set_error(message)

    def _set_loading(self, loading: bool) -> None:
        self.btn_refresh.setEnabled(not loading)
        if loading:
            self.btn_refresh.setText(L10N.ANALIZ_HESAPLANIYOR)
            self.btn_refresh.setIconName("refresh-cw", color="@BUTTON_DISABLED_TEXT", size=18)
        else:
            self.btn_refresh.setText(L10N.ANALIZI_YENILE_1)
            self.btn_refresh.setIconName("refresh-cw", color="@COLOR_TEXT_WHITE", size=18)
