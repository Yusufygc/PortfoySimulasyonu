from __future__ import annotations

from datetime import date

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from src.application.services.reporting.daily_history_models import ExportMode


class DashboardExportActions:
    def __init__(self, page) -> None:
        self._page = page

    def on_export_today(self) -> None:
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self._page, "Bilgi", "Herhangi bir işlem bulunamadı.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self._page,
            "Excel Dosyası Seç",
            "portfoy_takip.xlsx",
            "Excel Dosyaları (*.xlsx)",
        )
        if not file_path:
            return

        try:
            self._page.excel_export_service.export_history(
                start_date=first_date,
                end_date=date.today(),
                file_path=file_path,
                mode=ExportMode.OVERWRITE,
            )
            QMessageBox.information(self._page, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Excel hatası: {exc}")

    def on_export_range(self) -> None:
        first_date = self._page.portfolio_service.get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self._page, "Bilgi", "İşlem bulunamadı.")
            return

        dialog = self._page.date_range_dialog_cls(self._page, min_date=first_date, max_date=date.today())
        if dialog.exec_() != dialog.Accepted:
            return

        result = dialog.get_range()
        if not result:
            return
        start_date, end_date = result

        file_path, _ = QFileDialog.getSaveFileName(
            self._page,
            "Excel Seç",
            "portfoy_takip.xlsx",
            "Excel Dosyaları (*.xlsx)",
        )
        if not file_path:
            return

        try:
            self._page.excel_export_service.export_history(
                start_date=start_date,
                end_date=end_date,
                file_path=file_path,
                mode=ExportMode.OVERWRITE,
            )
            QMessageBox.information(self._page, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as exc:
            QMessageBox.critical(self._page, "Hata", f"Hata: {exc}")
