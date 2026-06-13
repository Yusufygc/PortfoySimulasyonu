# src/ui/pages/settings/price_data_panel.py
from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import date

from src.qt_compat.qtcore import QDate, QSize, Qt, QThreadPool
from src.qt_compat.qtwidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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
from src.ui.pages.settings.utils.price_data_scope import populate_scope_combo


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
        title = QLabel(L10N.FIYAT_VERISI_YONETIMI)
        title.setProperty("cssClass", "panelTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        self.chk_problem_only = QCheckBox(L10N.SADECE_SORUNLU_HISSELER)
        self.chk_problem_only.stateChanged.connect(self._report_renderer.populate_health_table)
        title_row.addWidget(self.chk_problem_only)
        layout.addLayout(title_row)

        desc = QLabel(
            L10N.KAYITLI_HISSELERIN_GUNLUK_FIYAT_VERISINI +
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
            self.detail_text.setText(L10N.FIYAT_VERISI_YONETIM_SERVISI_KULLANILAMIYOR)

    def _build_summary_grid(self) -> QGridLayout:
        summary_grid = QGridLayout()
        summary_grid.setSpacing(10)
        self.lbl_stock_count = self._summary_label(L10N.HISSE_1, "-", "list")
        self.lbl_missing_count = self._summary_label(L10N.EKSIK_GUN, "-", L10N.ALERTTRIANGLE)
        self.lbl_holiday_count = self._summary_label(L10N.BILINEN_TATIL, "-", "calendar")
        self.lbl_holiday_candidate_count = self._summary_label(L10N.TATIL_ADAYI, "-", "clock")
        self.lbl_latest_date = self._summary_label(L10N.SON_GUNCEL_TARIH, "-", "history")
        summary_grid.addWidget(self.lbl_stock_count, 0, 0)
        summary_grid.addWidget(self.lbl_missing_count, 0, 1)
        summary_grid.addWidget(self.lbl_holiday_count, 0, 2)
        summary_grid.addWidget(self.lbl_holiday_candidate_count, 0, 3)
        summary_grid.addWidget(self.lbl_latest_date, 0, 4)
        return summary_grid

    def _build_filter_row(self) -> QHBoxLayout:
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.combo_portfolio_scope = QComboBox()
        self.combo_portfolio_scope.setProperty("cssClass", "tradeInputNormal")
        self.combo_portfolio_scope.setMinimumHeight(36)
        populate_scope_combo(self.combo_portfolio_scope, self.price_data_health_service)

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

        self.combo_portfolio_scope.currentIndexChanged.connect(self._on_scope_changed)
        filter_row.addWidget(QLabel(L10N.PORTFOY))
        filter_row.addWidget(self.combo_portfolio_scope)
        filter_row.addWidget(QLabel(L10N.BASLANGIC))
        filter_row.addWidget(self.date_start)
        filter_row.addWidget(QLabel(L10N.BITIS))
        filter_row.addWidget(self.date_end)
        filter_row.addStretch()
        return filter_row

    def _build_action_row(self) -> QHBoxLayout:
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_analyze = self._action_button(L10N.ANALIZ_ET_1, "search", self._actions.analyze)
        self.btn_update_missing = self._action_button(
            L10N.TOPLU_EKSIKLERI_GUNCELLE, "refresh-cw", self._actions.update_missing
        )
        self.btn_update_selected = self._action_button(
            L10N.SECILI_HISSEYI_GUNCELLE, "refresh-cw", self._actions.update_selected
        )
        self.btn_update_selected.setVisible(False)
        self.btn_update_selected.setEnabled(False)
        self.btn_update_latest = self._action_button(
            L10N.SON_GUNDEN_BUGUNE_GUNCELLE, "calendar", self._actions.update_from_latest
        )
        self.btn_delete_range = self._action_button(
            L10N.ARALIGI_SIL, "trash-2", self._actions.delete_range, "dangerTextButton", "@COLOR_DANGER"
        )
        self.btn_copy_report = self._action_button(
            L10N.RAPORU_KOPYALA, L10N.FILETEXT, self._actions.copy_report
        )

        self.price_action_row = action_row
        for button in self._price_data_top_buttons:
            action_row.addWidget(button)
        action_row.addStretch()
        return action_row

    def _build_content_row(self) -> QHBoxLayout:
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        self.health_table = QTableWidget()
        self.health_table.setColumnCount(6)
        self.health_table.setHorizontalHeaderLabels(
            ["Hisse", L10N.SON_VERI, L10N.EKSIK_GUN, "Durum", L10N.ILK_EKSIK, L10N.SON_EKSIK]
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

        detail_panel = QFrame()
        detail_panel.setProperty("cssClass", "plainTextPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(10)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumWidth(280)
        self.detail_text.setFrameShape(QFrame.NoFrame)
        self.detail_text.setText(L10N.ANALIZ_SONUCU_BEKLENIYOR)
        detail_layout.addWidget(self.detail_text, 1)
        detail_layout.addWidget(self.btn_update_selected)

        content_row.addWidget(detail_panel, 1)
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
    def _price_data_top_buttons(self) -> tuple[AnimatedButton, ...]:
        return (
            self.btn_analyze,
            self.btn_update_missing,
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

    def _selected_scope(self) -> str:
        if not hasattr(self, "combo_portfolio_scope"):
            return "all_active"
        return self.combo_portfolio_scope.currentData() or "all_active"

    def _selected_scope_label(self) -> str:
        if not hasattr(self, "combo_portfolio_scope"):
            return L10N.TUM_AKTIF_PORTFOYLER
        return self.combo_portfolio_scope.currentText() or L10N.TUM_AKTIF_PORTFOYLER

    def _on_scope_changed(self) -> None:
        self._apply_minimum_start_date()
        self._report_renderer.clear_report()

    def _apply_minimum_start_date(self) -> None:
        default_date = QDate.currentDate().addDays(-90)
        self.date_start.setMinimumDate(QDate(1900, 1, 1))
        if self.price_data_health_service is None:
            self.date_start.setDate(default_date)
            return

        minimum_start = self.price_data_health_service.minimum_start_date(self._selected_scope())
        if minimum_start is None:
            self.date_start.setDate(default_date)
            return

        minimum_qdate = QDate(minimum_start.year, minimum_start.month, minimum_start.day)
        self.date_start.setMinimumDate(minimum_qdate)
        self.date_start.setDate(minimum_qdate)

    def _date_range(self) -> tuple[date, date]:
        start_date = self.date_start.date().toPyDate()
        end_date = self.date_end.date().toPyDate()
        minimum_start = (
            self.price_data_health_service.minimum_start_date(self._selected_scope())
            if self.price_data_health_service else None
        )
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

    def _set_selected_update_button_state(self, enabled: bool = True) -> None:
        has_selection = self._selected_stock_id() is not None
        self.btn_update_selected.setVisible(has_selection)
        self.btn_update_selected.setEnabled(enabled and has_selection)

    def _set_busy(self, busy: bool, text: str | None = None) -> None:
        self._set_price_data_controls_enabled(not busy)
        if text:
            self.detail_text.setText(text)

    def _set_price_data_controls_enabled(self, enabled: bool) -> None:
        for button in self._price_data_top_buttons:
            button.setEnabled(enabled)
        self._set_selected_update_button_state(enabled)
        self.combo_portfolio_scope.setEnabled(enabled)
        self.date_start.setEnabled(enabled)
        self.date_end.setEnabled(enabled)
        self.chk_problem_only.setEnabled(enabled)

    def _emit_prices_updated(self, result: PriceDataUpdateResult) -> None:
        publish_prices_updated(getattr(self.container, "event_bus", None), result.prices)

    # Proxy delegasyonları (testler tarafından kullanılıyor)
    def _apply_report(self, report: PriceDataHealthReport) -> None:
        self._report_renderer.apply_report(report)
