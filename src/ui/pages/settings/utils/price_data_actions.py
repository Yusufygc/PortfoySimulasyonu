from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QApplication, QMessageBox

from src.application.services.market.price_data_health_service import (
    PriceDataHealthReport,
    PriceDataUpdateResult,
)
from src.ui.widgets.shared import Toast
from src.ui.worker import Worker

if TYPE_CHECKING:
    from src.ui.pages.settings.price_data_panel import PriceDataPanel


class PriceDataActions:
    """Worker tabanlı işlem metodlarını yönetir (analiz, güncelleme, silme)."""

    def __init__(self, panel: PriceDataPanel) -> None:
        self.panel = panel

    def analyze(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            Toast.warning(panel, "Fiyat verisi yönetim servisi kullanılamıyor.")
            return
        start_date, end_date = panel._date_range()
        self._run_worker(
            panel.price_data_health_service.analyze,
            self._on_analyze_success,
            "Veri sağlığı analiz ediliyor...",
            start_date,
            end_date,
        )

    def update_missing(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        start_date, end_date = panel._date_range()
        self._run_worker(
            panel.price_data_health_service.update_missing_prices,
            self._on_update_success,
            "Eksik fiyatlar güncelleniyor...",
            start_date,
            end_date,
        )

    def update_selected(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        stock_id = panel._selected_stock_id()
        if stock_id is None:
            Toast.warning(panel, "Önce tablodan bir hisse seçin.")
            return
        start_date, end_date = panel._date_range()
        self._run_worker(
            panel.price_data_health_service.update_stock_range,
            self._on_update_success,
            "Seçili hisse güncelleniyor...",
            stock_id,
            start_date,
            end_date,
        )

    def update_from_latest(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        self._run_worker(
            panel.price_data_health_service.update_from_latest_to_today,
            self._on_update_success,
            "Son güncel günden bugüne eksikler tamamlanıyor...",
        )

    def delete_range(self) -> None:
        panel = self.panel
        if panel.price_data_health_service is None:
            return
        start_date, end_date = panel._date_range()
        reply = QMessageBox.question(
            panel,
            "Fiyat Verisini Sil",
            f"{start_date:%d.%m.%Y} - {end_date:%d.%m.%Y} aralığındaki fiyat kayıtları silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._run_worker(
            panel.price_data_health_service.delete_range,
            self._on_delete_success,
            "Fiyat kayıtları siliniyor...",
            start_date,
            end_date,
        )

    def copy_report(self) -> None:
        panel = self.panel
        if panel._current_report is None:
            Toast.warning(panel, "Kopyalanacak analiz raporu yok.")
            return
        QApplication.clipboard().setText(
            panel._report_renderer.format_report_text(panel._current_report)
        )
        Toast.success(panel, "Veri sağlığı raporu panoya kopyalandı.")

    def _run_worker(self, fn, success_slot, busy_text: str, *args) -> None:
        panel = self.panel
        panel._set_busy(True, busy_text)
        worker = Worker(fn, *args)
        worker.signals.result.connect(success_slot)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(lambda: panel._set_busy(False))
        panel.threadpool.start(worker)

    def _on_analyze_success(self, report: PriceDataHealthReport) -> None:
        self.panel._apply_report(report)
        Toast.success(self.panel, f"Analiz tamamlandı: {report.health_label}.")

    def _on_update_success(self, result: PriceDataUpdateResult) -> None:
        panel = self.panel
        panel._emit_prices_updated(result)
        if result.updated_count:
            Toast.success(
                panel,
                f"{result.updated_count} fiyat kaydı tamamlandı, "
                f"{result.skipped_holiday_count} tatil adayı atlandı.",
            )
        else:
            Toast.warning(panel, "Güncellenecek fiyat kaydı bulunamadı.")
            if result.errors:
                panel.detail_text.setText("Hata detayları:\n" + "\n".join(result.errors[:30]))
            return
        if result.errors:
            Toast.warning(panel, f"{len(result.errors)} veri kaynağı uyarısı oluştu.")
        self.analyze()

    def _on_delete_success(self, deleted_count: int) -> None:
        Toast.success(self.panel, f"{deleted_count} fiyat kaydı silindi.")
        self.analyze()

    def _on_worker_error(self, err_tuple) -> None:
        QMessageBox.critical(self.panel, "Hata", f"Hata:\n{err_tuple[1]}")
