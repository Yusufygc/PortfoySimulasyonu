from __future__ import annotations

import logging
from datetime import date, timedelta

from PyQt5.QtCore import QSize, Qt, QThreadPool
from PyQt5.QtWidgets import (
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
from src.ui.core.icon_manager import IconManager
from src.ui.pages.base_page import BasePage
from src.ui.worker import Worker

from .analysis_comparison_section import AnalysisComparisonSection
from .analysis_control_panel import AnalysisControlPanel
from .analysis_overview_section import AnalysisOverviewSection
from .analysis_risk_section import AnalysisRiskSection

logger = logging.getLogger(__name__)


class AnalysisPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Analiz"
        self.analysis_service = container.analysis_service
        self.threadpool = QThreadPool()
        self._request_seq = 0
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

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconManager.get_icon("line-chart", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28))
        header_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        lbl_title = QLabel("Analiz ve Kar\u015f\u0131la\u015ft\u0131rma")
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel("Portf\u00f6y, benchmark ve risk g\u00f6r\u00fcn\u00fcm\u00fcn\u00fc tek ak\u0131\u015fta inceleyin.")
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("Analizi Yenile")
        self.btn_refresh.setProperty("cssClass", "secondaryButton")
        self.btn_refresh.setIcon(IconManager.get_icon("refresh-cw", color="@COLOR_TEXT_PRIMARY"))
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
        self.comparison_section = AnalysisComparisonSection()
        self.risk_section = AnalysisRiskSection()
        self.tabs.addTab(self._wrap_scroll(self.overview_section), "Genel Bak\u0131\u015f")
        self.tabs.addTab(self._wrap_scroll(self.comparison_section), "Kar\u015f\u0131la\u015ft\u0131rma")
        self.tabs.addTab(self._wrap_scroll(self.risk_section), "Da\u011f\u0131l\u0131m & Risk")
        left_layout.addWidget(self.tabs, 1)
        content_layout.addWidget(left_container, 1)

        self.control_panel = AnalysisControlPanel()
        self.control_panel.filter_changed.connect(self._request_refresh)
        self.control_panel.source_changed.connect(self._on_source_changed)

        panel_min_width = self.control_panel.minimumWidth() + 20
        panel_max_width = self.control_panel.maximumWidth() + 20

        self.control_panel_scroll = QScrollArea()
        self.control_panel_scroll.setWidgetResizable(True)
        self.control_panel_scroll.setFrameShape(QFrame.NoFrame)
        self.control_panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.control_panel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.control_panel_scroll.setMinimumWidth(panel_min_width)
        self.control_panel_scroll.setMaximumWidth(panel_max_width)
        self.control_panel_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.control_panel_scroll.setWidget(self.control_panel)

        self.control_panel_column = QWidget()
        self.control_panel_column.setMinimumWidth(panel_min_width)
        self.control_panel_column.setMaximumWidth(panel_max_width)
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

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_static_options()
        self._sync_source_context()
        self._request_refresh()

    def _load_static_options(self) -> None:
        options = self.analysis_service.get_portfolio_options()
        self.control_panel.set_portfolio_options(options)
        self.control_panel.set_comparison_portfolios(options)
        self.control_panel.set_benchmarks(self.analysis_service.get_benchmark_definitions())

    def _sync_source_context(self) -> None:
        source = self.control_panel.selected_portfolio_source() or "dashboard"
        self.control_panel.set_stocks(self.analysis_service.get_stock_map_for_source(source))
        earliest = self.analysis_service.get_first_trade_date_for_source(source) or (date.today() - timedelta(days=365))
        self.control_panel.set_earliest_date(earliest)
        self.control_panel.set_comparison_portfolios(self.analysis_service.get_portfolio_options())

    def _on_source_changed(self, _source: str) -> None:
        self._sync_source_context()

    def _build_filter_state(self) -> AnalysisFilterState:
        start_date, end_date = self.control_panel.date_range()
        return AnalysisFilterState(
            start_date=start_date,
            end_date=end_date,
            selected_stock_ids=self.control_panel.selected_stock_ids(),
            view_mode=self.control_panel.view_mode(),
            selected_benchmarks=self.control_panel.selected_benchmarks(),
            portfolio_source=self.control_panel.selected_portfolio_source() or "dashboard",
            comparison_portfolio_sources=self.control_panel.selected_comparison_sources(),
        )

    def _request_refresh(self) -> None:
        filter_state = self._build_filter_state()
        if filter_state.start_date > filter_state.end_date:
            self._render_error("Ba\u015flang\u0131\u00e7 tarihi biti\u015f tarihinden sonra olamaz.")
            return

        self._request_seq += 1
        request_id = self._request_seq
        self._set_loading(True)

        worker = Worker(self.analysis_service.get_page_payload, filter_state)
        worker.signals.result.connect(lambda result, rid=request_id: self._on_payload_ready(rid, result))
        worker.signals.error.connect(lambda err, rid=request_id: self._on_payload_error(rid, err))
        worker.signals.finished.connect(lambda rid=request_id: self._on_payload_finished(rid))
        self.threadpool.start(worker)

    def _on_payload_ready(self, request_id: int, payload: dict) -> None:
        if request_id != self._request_seq:
            return
        self.warning_banner.hide()
        self.overview_section.set_data(payload["overview"])
        self.comparison_section.set_data(payload["comparison"])
        self.risk_section.set_data(payload["risk"])

    def _on_payload_error(self, request_id: int, err_tuple) -> None:
        if request_id != self._request_seq:
            return
        logger.error("Analiz y\u00fcklenemedi: %s", err_tuple[1], exc_info=True)
        self._render_error(str(err_tuple[1]))

    def _on_payload_finished(self, request_id: int) -> None:
        if request_id != self._request_seq:
            return
        self._set_loading(False)

    def _render_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.overview_section.set_error(message)
        self.comparison_section.set_error(message)
        self.risk_section.set_error(message)

    def _set_loading(self, loading: bool) -> None:
        self.btn_refresh.setEnabled(not loading)
        self.btn_refresh.setText("Y\u00fckleniyor..." if loading else "Analizi Yenile")
