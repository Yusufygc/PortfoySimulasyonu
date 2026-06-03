from __future__ import annotations

from PyQt5.QtCore import QSize
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QTabWidget

from .base_page import BasePage
from src.ui.core.icon_manager import IconManager
from src.ui.shared.live_price_refresh_controller import (
    DEFAULT_LIVE_PRICE_REFRESH_ENABLED,
    DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
    LIVE_PRICE_REFRESH_ENABLED_KEY,
    LIVE_PRICE_REFRESH_INTERVAL_KEY,
    LIVE_PRICE_REFRESH_INTERVAL_OPTIONS,
)
from src.ui.pages.settings import (
    AppearancePanel,
    CorporateActionCandidatesPanel,
    PriceDataPanel,
    ResetPanel,
)


class SettingsPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Ayarlar"
        self.reset_service = container.reset_service
        self.price_data_health_service = getattr(container, "price_data_health_service", None)
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._init_ui()
        self._bind_price_data_compatibility_aliases()

    def _init_ui(self) -> None:
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(
            IconManager.get_icon("save", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28)
        )
        header.addWidget(icon_label)

        title_label = QLabel("Ayarlar")
        title_label.setProperty("cssClass", "pageTitle")
        header.addWidget(title_label)
        header.addStretch()
        self.main_layout.addLayout(header)

        description = QLabel(
            "Uygulama genel aksiyonlarını, veri sağlığını ve sistem seviyesindeki işlemleri buradan yönetin."
        )
        description.setWordWrap(True)
        description.setProperty("cssClass", "pageDescription")
        self.main_layout.addWidget(description)

        self.main_layout.addLayout(self._build_live_price_refresh_controls())

        self.tabs = QTabWidget()
        self.tabs.setProperty("cssClass", "mainTabWidget")

        self.home_tab = ResetPanel(self.reset_service, self)
        self.appearance_tab = AppearancePanel(self)
        self.price_data_tab = PriceDataPanel(self.container, self.price_data_health_service, self)
        self.corporate_action_candidates_tab = CorporateActionCandidatesPanel(self.container, self)

        self.tabs.addTab(self.home_tab, "Ana Sayfa")
        self.tabs.addTab(self.appearance_tab, "Görünüm")
        self.tabs.addTab(self.price_data_tab, "Fiyat Verisi Yönetimi")
        self.tabs.addTab(self.corporate_action_candidates_tab, "Kurumsal Aksiyonlar")

        self.tabs.currentChanged.connect(self._update_tab_icons)
        self._update_tab_icons()
        self.main_layout.addWidget(self.tabs, 1)

    def _build_live_price_refresh_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.chk_live_price_refresh = QCheckBox("Otomatik fiyat yenileme")
        self.chk_live_price_refresh.setChecked(self._live_price_refresh_enabled())
        self.chk_live_price_refresh.stateChanged.connect(self._on_live_price_refresh_settings_changed)

        self.combo_live_price_refresh_interval = QComboBox()
        self.combo_live_price_refresh_interval.setProperty("cssClass", "tradeInputNormal")
        current_interval = self._live_price_refresh_interval()
        for minutes in LIVE_PRICE_REFRESH_INTERVAL_OPTIONS:
            self.combo_live_price_refresh_interval.addItem(f"{minutes} dk", minutes)
        selected_index = self.combo_live_price_refresh_interval.findData(current_interval)
        self.combo_live_price_refresh_interval.setCurrentIndex(max(0, selected_index))
        self.combo_live_price_refresh_interval.currentIndexChanged.connect(
            self._on_live_price_refresh_settings_changed
        )

        row.addWidget(self.chk_live_price_refresh)
        row.addWidget(QLabel("Aralık"))
        row.addWidget(self.combo_live_price_refresh_interval)
        row.addStretch()
        return row

    def _live_price_refresh_enabled(self) -> bool:
        value = self._settings.value(
            LIVE_PRICE_REFRESH_ENABLED_KEY,
            DEFAULT_LIVE_PRICE_REFRESH_ENABLED,
        )
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "hayir", "hayır", "no", "off"}
        return bool(value)

    def _live_price_refresh_interval(self) -> int:
        value = self._settings.value(
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
            DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
        )
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            minutes = DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES
        return minutes if minutes in LIVE_PRICE_REFRESH_INTERVAL_OPTIONS else DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES

    def _on_live_price_refresh_settings_changed(self) -> None:
        self._settings.setValue(LIVE_PRICE_REFRESH_ENABLED_KEY, self.chk_live_price_refresh.isChecked())
        self._settings.setValue(
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
            self.combo_live_price_refresh_interval.currentData() or DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
        )
        self._settings.sync()
        window = self.window()
        if hasattr(window, "reload_live_price_refresh_settings"):
            window.reload_live_price_refresh_settings()

    def _update_tab_icons(self, index: int = -1) -> None:
        idx = self.tabs.currentIndex() if index == -1 else index
        c0 = "@COLOR_TEXT_WHITE" if idx == 0 else "@COLOR_TEXT_SECONDARY"
        c1 = "@COLOR_TEXT_WHITE" if idx == 1 else "@COLOR_TEXT_SECONDARY"
        c2 = "@COLOR_TEXT_WHITE" if idx == 2 else "@COLOR_TEXT_SECONDARY"
        c3 = "@COLOR_TEXT_WHITE" if idx == 3 else "@COLOR_TEXT_SECONDARY"
        self.tabs.setTabIcon(0, IconManager.get_icon("home", color=c0, size=QSize(18, 18)))
        self.tabs.setTabIcon(1, IconManager.get_icon("layers", color=c1, size=QSize(18, 18)))
        self.tabs.setTabIcon(2, IconManager.get_icon("bar-chart-2", color=c2, size=QSize(18, 18)))
        self.tabs.setTabIcon(3, IconManager.get_icon("clipboard-list", color=c3, size=QSize(18, 18)))

    def changeEvent(self, event):
        from PyQt5.QtCore import QEvent

        if event.type() == QEvent.StyleChange:
            self._update_tab_icons()
        super().changeEvent(event)

    def _bind_price_data_compatibility_aliases(self) -> None:
        for name in (
            "threadpool",
            "chk_problem_only",
            "lbl_stock_count",
            "lbl_missing_count",
            "lbl_holiday_count",
            "lbl_holiday_candidate_count",
            "lbl_latest_date",
            "combo_portfolio_scope",
            "date_start",
            "date_end",
            "btn_analyze",
            "btn_update_missing",
            "btn_update_selected",
            "btn_update_latest",
            "btn_delete_range",
            "btn_copy_report",
            "health_table",
            "detail_text",
        ):
            setattr(self, name, getattr(self.price_data_tab, name))

        self.btn_reset = self.home_tab.btn_reset

    @property
    def _current_report(self):
        return self.price_data_tab._current_report

    @_current_report.setter
    def _current_report(self, value) -> None:
        if hasattr(self, "price_data_tab"):
            self.price_data_tab._current_report = value

    def _apply_report(self, report) -> None:
        return self.price_data_tab._apply_report(report)

    def _populate_health_table(self) -> None:
        return self.price_data_tab._populate_health_table()

    def _selected_stock_id(self) -> int | None:
        return self.price_data_tab._selected_stock_id()

    def _format_report_text(self, report) -> str:
        return self.price_data_tab._format_report_text(report)
