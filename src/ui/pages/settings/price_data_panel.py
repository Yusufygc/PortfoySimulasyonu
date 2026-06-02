# src/ui/pages/settings/price_data_panel.py
from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QDate, QSize, Qt, QThreadPool
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.application.services.market.price_data_health_service import (
    PriceDataHealthReport,
    PriceDataUpdateResult,
)
from src.ui.core.icon_manager import IconManager
from src.ui.shared.price_event_publisher import publish_prices_updated
from src.ui.widgets.shared import AnimatedButton, Toast

from src.ui.pages.settings.utils.price_data_actions import PriceDataActions
from src.ui.pages.settings.utils.price_data_report import PriceDataReportRenderer


class PriceDataPanel(QWidget):
    """
    Fiyat verisi yönetimi paneli (Orchestrator).
    UI kurulumunu yapar, durumu tutar. İşlemleri PriceDataActions'a,
    renderlamayı PriceDataReportRenderer'a delege eder.
    """
    def __init__(self, container, price_data_health_service=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.price_data_health_service = price_data_health_service
        self.threadpool = QThreadPool.globalInstance()
        self._current_report: PriceDataHealthReport | None = None

        self._actions = PriceDataActions(self)
        self._report_renderer = PriceDataReportRenderer(self)

        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(18)

        card = QFrame()
        card.setProperty("cssClass", "panelFramePadded")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title = QLabel("Fiyat Verisi Yönetimi")
        title.setProperty("cssClass", "panelTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        self.chk_problem_only = QCheckBox("Sadece sorunlu hisseler")
        self.chk_problem_only.stateChanged.connect(self._report_renderer.populate_health_table)
        title_row.addWidget(self.chk_problem_only)
        layout.addLayout(title_row)

        desc = QLabel(
            "Kayıtlı hisselerin günlük fiyat verisini analiz eder; eksik kayıtları, hafta sonlarını "
            "ve tüm piyasada boş kalan tatil/kapalı gün adaylarını ayırır."
        )
        desc.setWordWrap(True)
        desc.setProperty("cssClass", "pageDescription")
        layout.addWidget(desc)

        layout.addLayout(self._build_summary_grid())
        layout.addLayout(self._build_filter_row())
        layout.addLayout(self._build_action_row())
        layout.addLayout(self._build_content_row())

        root_layout.addWidget(card)
        if self.price_data_health_service is None:
            self._set_price_data_controls_enabled(False)
            self.detail_text.setText("Fiyat verisi yönetim servisi kullanılamıyor.")

    def _build_summary_grid(self) -> QGridLayout:
        summary_grid = QGridLayout()
        summary_grid.setSpacing(10)
        self.lbl_stock_count = self._summary_label("Hisse", "-", "list")
        self.lbl_missing_count = self._summary_label("Eksik Gün", "-", "alert-triangle")
        self.lbl_holiday_count = self._summary_label("Bilinen Tatil", "-", "calendar")
        self.lbl_holiday_candidate_count = self._summary_label("Tatil Adayı", "-", "clock")
        self.lbl_latest_date = self._summary_label("Son Güncel Tarih", "-", "history")
        summary_grid.addWidget(self.lbl_stock_count, 0, 0)
        summary_grid.addWidget(self.lbl_missing_count, 0, 1)
        summary_grid.addWidget(self.lbl_holiday_count, 0, 2)
        summary_grid.addWidget(self.lbl_holiday_candidate_count, 0, 3)
        summary_grid.addWidget(self.lbl_latest_date, 0, 4)
        return summary_grid

    def _build_filter_row(self) -> QHBoxLayout:
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setProperty("cssClass", "tradeInputNormal")
        self.date_start.setMinimumHeight(36)
        self._apply_minimum_start_date()

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setProperty("cssClass", "tradeInputNormal")
        self.date_end.setMinimumHeight(36)
        self.date_end.setDate(QDate.currentDate())

        filter_row.addWidget(QLabel("Başlangıç"))
        filter_row.addWidget(self.date_start)
        filter_row.addWidget(QLabel("Bitiş"))
        filter_row.addWidget(self.date_end)
        filter_row.addStretch()
        return filter_row

    def _build_action_row(self) -> QHBoxLayout:
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_analyze = self._action_button(" Analiz Et", "search", self._actions.analyze)
        self.btn_update_missing = self._action_button(
            " Toplu Eksikleri Güncelle", "refresh-cw", self._actions.update_missing
        )
        self.btn_update_selected = self._action_button(
            " Seçili Hisseyi Güncelle", "refresh-cw", self._actions.update_selected
        )
        self.btn_update_latest = self._action_button(
            " Son Günden Bugüne Güncelle", "calendar", self._actions.update_from_latest
        )
        self.btn_delete_range = self._action_button(
            " Aralığı Sil", "trash-2", self._actions.delete_range, "dangerTextButton", "@COLOR_DANGER"
        )
        self.btn_copy_report = self._action_button(
            " Raporu Kopyala", "file-text", self._actions.copy_report
        )

        for button in self._price_data_buttons:
            action_row.addWidget(button)
        action_row.addStretch()
        return action_row

    def _build_content_row(self) -> QHBoxLayout:
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        self.health_table = QTableWidget()
        self.health_table.setColumnCount(6)
        self.health_table.setHorizontalHeaderLabels(
            ["Hisse", "Son Veri", "Eksik Gün", "Durum", "İlk Eksik", "Son Eksik"]
        )
        self.health_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.health_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.health_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.health_table.verticalHeader().setVisible(False)

        header = self.health_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.health_table.setProperty("cssClass", "dataTable")
        self.health_table.itemSelectionChanged.connect(self._report_renderer.on_health_selection_changed)
        content_row.addWidget(self.health_table, 3)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumWidth(280)
        self.detail_text.setProperty("cssClass", "plainTextPanel")
        self.detail_text.setText("Analiz sonucu bekleniyor.")
        content_row.addWidget(self.detail_text, 1)
        return content_row

    def _action_button(
        self,
        text: str,
        icon_name: str,
        slot,
        css_class: str = "secondaryButton",
        icon_color: str = "@COLOR_TEXT_PRIMARY",
    ) -> AnimatedButton:
        button = AnimatedButton(text)
        button.setIconName(icon_name, color=icon_color)
        button.setProperty("cssClass", css_class)
        button.clicked.connect(slot)
        return button

    @property
    def _price_data_buttons(self) -> tuple[AnimatedButton, ...]:
        return (
            self.btn_analyze,
            self.btn_update_missing,
            self.btn_update_selected,
            self.btn_update_latest,
            self.btn_delete_range,
            self.btn_copy_report,
        )

    def _summary_label(self, title: str, value: str, icon_name: str = None) -> QFrame:
        frame = QFrame()
        frame.setProperty("cssClass", "infoCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        if icon_name:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(
                IconManager.get_icon(icon_name, color="@COLOR_ACCENT", size=QSize(18, 18)).pixmap(18, 18)
            )
            title_row.addWidget(icon_lbl)

        caption = QLabel(title)
        caption.setProperty("cssClass", "cardTitle")
        title_row.addWidget(caption)
        title_row.addStretch()
        layout.addLayout(title_row)

        metric = QLabel(value)
        metric.setObjectName("metricValue")
        metric.setProperty("cssClass", "metricValue")
        layout.addWidget(metric)
        frame.metric_label = metric
        return frame

    # ------------------------------------------------------------------
    # Durum ve Proxy Metodları (Testler ve UI State İçin)
    # ------------------------------------------------------------------

    def _apply_minimum_start_date(self) -> None:
        default_date = QDate.currentDate().addDays(-90)
        if self.price_data_health_service is None:
            self.date_start.setDate(default_date)
            return

        minimum_start = self.price_data_health_service.minimum_start_date()
        if minimum_start is None:
            self.date_start.setDate(default_date)
            return

        minimum_qdate = QDate(minimum_start.year, minimum_start.month, minimum_start.day)
        self.date_start.setMinimumDate(minimum_qdate)
        self.date_start.setDate(minimum_qdate if default_date < minimum_qdate else default_date)

    def _date_range(self) -> tuple[date, date]:
        start_date = self.date_start.date().toPyDate()
        end_date = self.date_end.date().toPyDate()
        minimum_start = self.price_data_health_service.minimum_start_date() if self.price_data_health_service else None
        if minimum_start and start_date < minimum_start:
            start_date = minimum_start
            self.date_start.setDate(QDate(minimum_start.year, minimum_start.month, minimum_start.day))
            Toast.warning(
                self,
                f"Başlangıç tarihi portföye ilk hisse eklenme tarihinden önce olamaz ({minimum_start:%d.%m.%Y}).",
            )
        return start_date, end_date

    def _selected_stock_id(self) -> int | None:
        selected = self.health_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.health_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _set_busy(self, busy: bool, text: str | None = None) -> None:
        self._set_price_data_controls_enabled(not busy)
        if text:
            self.detail_text.setText(text)

    def _set_price_data_controls_enabled(self, enabled: bool) -> None:
        for button in self._price_data_buttons:
            button.setEnabled(enabled)
        self.date_start.setEnabled(enabled)
        self.date_end.setEnabled(enabled)
        self.chk_problem_only.setEnabled(enabled)

    def _emit_prices_updated(self, result: PriceDataUpdateResult) -> None:
        publish_prices_updated(getattr(self.container, "event_bus", None), result.prices)

    # Proxy delegasyonları (testler tarafından kullanılıyor)
    def _apply_report(self, report: PriceDataHealthReport) -> None:
        self._report_renderer.apply_report(report)
