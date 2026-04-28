from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QDate, QSize, Qt, QThreadPool
from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base_page import BasePage
from src.application.services.market.price_data_health_service import PriceDataHealthReport, PriceDataUpdateResult
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared import AnimatedButton, Toast
from src.ui.worker import Worker


class SettingsPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Ayarlar"
        self.reset_service = container.reset_service
        self.price_data_health_service = getattr(container, "price_data_health_service", None)
        self.threadpool = QThreadPool()
        self._current_report: PriceDataHealthReport | None = None
        self._init_ui()

    def _init_ui(self):
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

        self.tabs = QTabWidget()
        self.tabs.setProperty("cssClass", "mainTabs")

        self.home_tab = QWidget()
        self.home_layout = QVBoxLayout(self.home_tab)
        self.home_layout.setContentsMargins(0, 0, 0, 0)
        self.home_layout.setSpacing(18)
        self._create_reset_card(self.home_layout)
        self.home_layout.addStretch()

        self.price_data_tab = QWidget()
        self.price_data_layout = QVBoxLayout(self.price_data_tab)
        self.price_data_layout.setContentsMargins(0, 0, 0, 0)
        self.price_data_layout.setSpacing(18)
        self._create_price_data_card(self.price_data_layout)

        self.tabs.addTab(self.home_tab, IconManager.get_icon("home", color="@COLOR_TEXT_SECONDARY", size=QSize(18, 18)), "Ana Sayfa")
        self.tabs.addTab(self.price_data_tab, IconManager.get_icon("bar-chart-2", color="@COLOR_TEXT_SECONDARY", size=QSize(18, 18)), "Fiyat Verisi Yönetimi")
        self.main_layout.addWidget(self.tabs, 1)

    def _create_price_data_card(self, parent_layout: QVBoxLayout) -> None:
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
        self.chk_problem_only.stateChanged.connect(self._populate_health_table)
        title_row.addWidget(self.chk_problem_only)
        layout.addLayout(title_row)

        desc = QLabel(
            "Kayıtlı hisselerin günlük fiyat verisini analiz eder; eksik kayıtları, hafta sonlarını "
            "ve tüm piyasada boş kalan tatil/kapalı gün adaylarını ayırır."
        )
        desc.setWordWrap(True)
        desc.setProperty("cssClass", "pageDescription")
        layout.addWidget(desc)

        summary_grid = QGridLayout()
        summary_grid.setSpacing(10)
        self.lbl_stock_count = self._summary_label("Hisse", "-", "list")
        self.lbl_missing_count = self._summary_label("Eksik Gün", "-", "alert-triangle")
        self.lbl_holiday_count = self._summary_label("Tatil Adayı", "-", "calendar")
        self.lbl_latest_date = self._summary_label("Son Güncel Tarih", "-", "history")
        summary_grid.addWidget(self.lbl_stock_count, 0, 0)
        summary_grid.addWidget(self.lbl_missing_count, 0, 1)
        summary_grid.addWidget(self.lbl_holiday_count, 0, 2)
        summary_grid.addWidget(self.lbl_latest_date, 0, 3)
        layout.addLayout(summary_grid)

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
        layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.btn_analyze = AnimatedButton(" Analiz Et")
        self.btn_analyze.setIconName("search", color="@COLOR_TEXT_PRIMARY")
        self.btn_analyze.setProperty("cssClass", "secondaryButton")
        self.btn_analyze.clicked.connect(self._on_analyze)

        self.btn_update_missing = AnimatedButton(" Toplu Eksikleri Güncelle")
        self.btn_update_missing.setIconName("refresh-cw", color="@COLOR_TEXT_PRIMARY")
        self.btn_update_missing.setProperty("cssClass", "secondaryButton")
        self.btn_update_missing.clicked.connect(self._on_update_missing)

        self.btn_update_selected = AnimatedButton(" Seçili Hisseyi Güncelle")
        self.btn_update_selected.setIconName("refresh-cw", color="@COLOR_TEXT_PRIMARY")
        self.btn_update_selected.setProperty("cssClass", "secondaryButton")
        self.btn_update_selected.clicked.connect(self._on_update_selected_stock)

        self.btn_update_latest = AnimatedButton(" Son Günden Bugüne Güncelle")
        self.btn_update_latest.setIconName("calendar", color="@COLOR_TEXT_PRIMARY")
        self.btn_update_latest.setProperty("cssClass", "secondaryButton")
        self.btn_update_latest.clicked.connect(self._on_update_from_latest)

        self.btn_delete_range = AnimatedButton(" Aralığı Sil")
        self.btn_delete_range.setIconName("trash-2", color="@COLOR_DANGER")
        self.btn_delete_range.setProperty("cssClass", "dangerTextButton")
        self.btn_delete_range.clicked.connect(self._on_delete_range)

        self.btn_copy_report = AnimatedButton(" Raporu Kopyala")
        self.btn_copy_report.setIconName("file-text", color="@COLOR_TEXT_PRIMARY")
        self.btn_copy_report.setProperty("cssClass", "secondaryButton")
        self.btn_copy_report.clicked.connect(self._on_copy_report)

        for button in (
            self.btn_analyze,
            self.btn_update_missing,
            self.btn_update_selected,
            self.btn_update_latest,
            self.btn_delete_range,
            self.btn_copy_report,
        ):
            action_row.addWidget(button)
        action_row.addStretch()
        layout.addLayout(action_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(12)
        self.health_table = QTableWidget()
        self.health_table.setColumnCount(6)
        self.health_table.setHorizontalHeaderLabels(["Hisse", "Son Veri", "Eksik Gün", "Durum", "İlk Eksik", "Son Eksik"])
        self.health_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.health_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.health_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.health_table.verticalHeader().setVisible(False)
        
        from PyQt5.QtWidgets import QHeaderView
        header = self.health_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)      # Hisse
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Son Veri
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Eksik Gün
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Durum
        header.setSectionResizeMode(4, QHeaderView.Stretch)      # İlk Eksik
        header.setSectionResizeMode(5, QHeaderView.Stretch)      # Son Eksik
        
        self.health_table.setProperty("cssClass", "dataTable")
        self.health_table.itemSelectionChanged.connect(self._on_health_selection_changed)
        content_row.addWidget(self.health_table, 3)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumWidth(280)
        self.detail_text.setProperty("cssClass", "plainTextPanel")
        self.detail_text.setText("Analiz sonucu bekleniyor.")
        content_row.addWidget(self.detail_text, 1)
        layout.addLayout(content_row)

        parent_layout.addWidget(card)
        if self.price_data_health_service is None:
            self._set_price_data_controls_enabled(False)
            self.detail_text.setText("Fiyat verisi yönetim servisi kullanılamıyor.")

    def _create_reset_card(self, parent_layout: QVBoxLayout) -> None:
        reset_card = QFrame()
        reset_card.setProperty("cssClass", "panelFramePadded")
        reset_layout = QVBoxLayout(reset_card)
        reset_layout.setContentsMargins(20, 20, 20, 20)
        reset_layout.setSpacing(12)

        reset_title = QLabel("Sistem Sıfırlama")
        reset_title.setProperty("cssClass", "panelTitle")
        reset_layout.addWidget(reset_title)

        reset_text = QLabel(
            "Tüm portföy, fiyat ve hisse verilerini siler. "
            "Bu işlem geri alınmaz."
        )
        reset_text.setWordWrap(True)
        reset_text.setProperty("cssClass", "pageDescription")
        reset_layout.addWidget(reset_text)

        action_row = QHBoxLayout()
        action_row.addStretch()

        self.btn_reset = AnimatedButton(" Sistemi Sıfırla")
        self.btn_reset.setIconName("trash-2", color="@COLOR_DANGER")
        self.btn_reset.setProperty("cssClass", "dangerTextButton")
        self.btn_reset.clicked.connect(self._on_reset)
        action_row.addWidget(self.btn_reset)

        reset_layout.addLayout(action_row)
        parent_layout.addWidget(reset_card)

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

    def _on_analyze(self) -> None:
        if self.price_data_health_service is None:
            Toast.warning(self, "Fiyat verisi yönetim servisi kullanılamıyor.")
            return
        start_date, end_date = self._date_range()
        self._run_worker(
            self.price_data_health_service.analyze,
            self._on_analyze_success,
            "Veri sağlığı analiz ediliyor...",
            start_date,
            end_date,
        )

    def _on_update_missing(self) -> None:
        if self.price_data_health_service is None:
            return
        start_date, end_date = self._date_range()
        self._run_worker(
            self.price_data_health_service.update_missing_prices,
            self._on_update_success,
            "Eksik fiyatlar güncelleniyor...",
            start_date,
            end_date,
        )

    def _on_update_selected_stock(self) -> None:
        if self.price_data_health_service is None:
            return
        stock_id = self._selected_stock_id()
        if stock_id is None:
            Toast.warning(self, "Önce tablodan bir hisse seçin.")
            return
        start_date, end_date = self._date_range()
        self._run_worker(
            self.price_data_health_service.update_stock_range,
            self._on_update_success,
            "Seçili hisse güncelleniyor...",
            stock_id,
            start_date,
            end_date,
        )

    def _on_update_from_latest(self) -> None:
        if self.price_data_health_service is None:
            return
        self._run_worker(
            self.price_data_health_service.update_from_latest_to_today,
            self._on_update_success,
            "Son güncel günden bugüne eksikler tamamlanıyor...",
        )

    def _on_delete_range(self) -> None:
        if self.price_data_health_service is None:
            return
        start_date, end_date = self._date_range()
        reply = QMessageBox.question(
            self,
            "Fiyat Verisini Sil",
            f"{start_date:%d.%m.%Y} - {end_date:%d.%m.%Y} aralığındaki fiyat kayıtları silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._run_worker(
            self.price_data_health_service.delete_range,
            self._on_delete_success,
            "Fiyat kayıtları siliniyor...",
            start_date,
            end_date,
        )

    def _on_copy_report(self) -> None:
        if self._current_report is None:
            Toast.warning(self, "Kopyalanacak analiz raporu yok.")
            return
        QApplication.clipboard().setText(self._format_report_text(self._current_report))
        Toast.success(self, "Veri sağlığı raporu panoya kopyalandı.")

    def _run_worker(self, fn, success_slot, busy_text: str, *args) -> None:
        self._set_busy(True, busy_text)
        worker = Worker(fn, *args)
        worker.signals.result.connect(success_slot)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(lambda: self._set_busy(False))
        self.threadpool.start(worker)

    def _on_analyze_success(self, report: PriceDataHealthReport) -> None:
        self._apply_report(report)
        Toast.success(self, f"Analiz tamamlandı: {report.health_label}.")

    def _on_update_success(self, result: PriceDataUpdateResult) -> None:
        self._emit_prices_updated(result)
        if result.updated_count:
            Toast.success(
                self,
                f"{result.updated_count} fiyat kaydı tamamlandı, {result.skipped_holiday_count} tatil adayı atlandı.",
            )
        else:
            Toast.warning(self, "Güncellenecek fiyat kaydı bulunamadı.")
            if result.errors:
                self.detail_text.setText("Hata detayları:\n" + "\n".join(result.errors[:30]))
            return
        if result.errors:
            Toast.warning(self, f"{len(result.errors)} veri kaynağı uyarısı oluştu.")
        self._on_analyze()

    def _on_delete_success(self, deleted_count: int) -> None:
        Toast.success(self, f"{deleted_count} fiyat kaydı silindi.")
        self._on_analyze()

    def _on_worker_error(self, err_tuple) -> None:
        QMessageBox.critical(self, "Hata", f"Hata:\n{err_tuple[1]}")

    def _apply_report(self, report: PriceDataHealthReport) -> None:
        self._current_report = report
        self.lbl_stock_count.metric_label.setText(str(report.total_stock_count))
        self.lbl_missing_count.metric_label.setText(str(report.total_missing_count))
        self.lbl_holiday_count.metric_label.setText(str(report.holiday_candidate_count))
        self.lbl_latest_date.metric_label.setText(report.latest_price_date.strftime("%d.%m.%Y") if report.latest_price_date else "-")
        self._populate_health_table()
        self.detail_text.setHtml(self._format_report_text(report))

    def _populate_health_table(self) -> None:
        if self._current_report is None:
            return
        only_problem = self.chk_problem_only.isChecked()
        rows = [
            row
            for row in self._current_report.rows
            if not only_problem or row.missing_count > 0
        ]
        self.health_table.setRowCount(len(rows))
        
        from PyQt5.QtGui import QColor, QFont
        
        for row_index, row in enumerate(rows):
            values = [
                row.ticker,
                row.last_price_date.strftime("%d.%m.%Y") if row.last_price_date else "-",
                str(row.missing_count),
                row.status,
                row.first_missing_date.strftime("%d.%m.%Y") if row.first_missing_date else "-",
                row.last_missing_date.strftime("%d.%m.%Y") if row.last_missing_date else "-",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
                if column == 0:
                    item.setData(Qt.UserRole, row.stock_id)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(QColor("#3b82f6")) # Primary Blue
                
                if column == 3: # Durum
                    if "Sağlıklı" in value:
                        item.setForeground(QColor("#10b981")) # Success Green
                    else:
                        item.setForeground(QColor("#ef4444")) # Danger Red
                
                if column == 2: # Eksik Gün
                    if row.missing_count > 0:
                        item.setForeground(QColor("#ef4444"))
                
                self.health_table.setItem(row_index, column, item)

    def _on_health_selection_changed(self) -> None:
        if self._current_report is None:
            return
        stock_id = self._selected_stock_id()
        if stock_id is None:
            return
        row = next((item for item in self._current_report.rows if item.stock_id == stock_id), None)
        if row is None:
            return
        
        missing_text = ", ".join(point_date.strftime("%d.%m.%Y") for point_date in row.missing_dates[:80])
        if row.missing_count > 80:
            missing_text += f"<br>... +{row.missing_count - 80} gün"
        if not missing_text:
            missing_text = "<span style='color: #94a3b8;'>Eksik gün yok.</span>"
        
        holiday_text = ", ".join(point_date.strftime("%d.%m.%Y") for point_date in self._current_report.holiday_candidate_dates[:60])
        if not holiday_text:
            holiday_text = "<span style='color: #94a3b8;'>Tatil/kapalı gün adayı yok.</span>"
            
        status_color = "#10b981" if "Sağlıklı" in row.status else "#ef4444"
        
        html = f"""
        <div style='font-family: Segoe UI, Arial; line-height: 1.4;'>
            <h3 style='color: #3b82f6; margin-bottom: 4px;'>{row.ticker}</h3>
            <div style='margin-bottom: 12px;'>
                <b>Durum:</b> <span style='color: {status_color};'>{row.status}</span><br>
                <b>Son Veri:</b> {row.last_price_date.strftime('%d.%m.%Y') if row.last_price_date else '-'}
            </div>
            
            <div style='margin-bottom: 12px;'>
                <b style='color: #ef4444;'>Eksik Günler ({row.missing_count}):</b><br>
                <div style='color: #cbd5e1; font-size: 13px;'>{missing_text}</div>
            </div>
            
            <div>
                <b style='color: #ca8a04;'>Tatil/Kapalı Gün Adayları:</b><br>
                <div style='color: #cbd5e1; font-size: 13px;'>{holiday_text}</div>
            </div>
        </div>
        """
        self.detail_text.setHtml(html)

    def _selected_stock_id(self) -> int | None:
        selected = self.health_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.health_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _format_report_text(self, report: PriceDataHealthReport) -> str:
        problematic = [row for row in report.rows if row.missing_count > 0]
        holidays = ", ".join(point_date.strftime("%d.%m.%Y") for point_date in report.holiday_candidate_dates[:40])
        if len(report.holiday_candidate_dates) > 40:
            holidays += f"<br>... +{len(report.holiday_candidate_dates) - 40} gün"
        
        status_color = "#10b981" if "Sağlıklı" in report.health_label else "#ef4444"
        
        problematic_html = ""
        if problematic:
            for row in problematic[:20]:
                problematic_html += f"<li>{row.ticker}: <span style='color: #ef4444;'>{row.missing_count} eksik</span></li>"
            if len(problematic) > 20:
                problematic_html += f"<li>... ve {len(problematic) - 20} hisse daha</li>"
        else:
            problematic_html = "<li>Yok</li>"

        html = f"""
        <div style='font-family: Segoe UI, Arial; line-height: 1.4;'>
            <h3 style='color: #3b82f6; margin-top: 0;'>Fiyat Verisi Sağlık Raporu</h3>
            <div style='margin-bottom: 12px;'>
                <b>Aralık:</b> {report.start_date:%d.%m.%Y} - {report.end_date:%d.%m.%Y}<br>
                <b>Durum:</b> <span style='color: {status_color}; font-weight: bold;'>{report.health_label}</span>
            </div>
            
            <div style='margin-bottom: 12px;'>
                <b>Hisse:</b> {report.total_stock_count}<br>
                <b>Beklenen İşlem Günü:</b> {report.expected_business_day_count}<br>
                <b>Eksik Kayıt:</b> <span style='color: #ef4444;'>{report.total_missing_count}</span><br>
                <b>Tatil Adayı:</b> <span style='color: #ca8a04;'>{report.holiday_candidate_count}</span>
            </div>
            
            <div style='margin-bottom: 12px;'>
                <b style='color: #ef4444;'>Sorunlu Hisseler:</b>
                <ul style='margin-top: 4px; padding-left: 20px; color: #cbd5e1;'>
                    {problematic_html}
                </ul>
            </div>
            
            <div>
                <b style='color: #ca8a04;'>Tatil/Kapalı Gün Adayları:</b><br>
                <div style='color: #cbd5e1; font-size: 13px;'>{holidays or "Yok"}</div>
            </div>
        </div>
        """
        return html

    def _set_busy(self, busy: bool, text: str | None = None) -> None:
        self._set_price_data_controls_enabled(not busy)
        if text:
            self.detail_text.setText(text)

    def _set_price_data_controls_enabled(self, enabled: bool) -> None:
        for button in (
            self.btn_analyze,
            self.btn_update_missing,
            self.btn_update_selected,
            self.btn_update_latest,
            self.btn_delete_range,
            self.btn_copy_report,
        ):
            button.setEnabled(enabled)
        self.date_start.setEnabled(enabled)
        self.date_end.setEnabled(enabled)
        self.chk_problem_only.setEnabled(enabled)

    def _emit_prices_updated(self, result: PriceDataUpdateResult) -> None:
        if result.prices and getattr(self.container, "event_bus", None):
            self.container.event_bus.prices_updated.emit(result.prices)

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            "Portföyü Sıfırla",
            "TÜM veriler silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.reset_service.reset_all()
            Toast.success(self, "Sistem başarıyla sıfırlandı.")
        except Exception as exc:
            Toast.error(self, f"Sistem sıfırlanamadı: {exc}")
