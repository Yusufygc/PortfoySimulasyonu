from src.ui.shared.locale_tr import L10N
# src/ui/pages/model_portfolio/utils/portfolio_exporter.py

import logging
from datetime import date
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog

from src.application.services.reporting.daily_history_models import ExportMode

logger = logging.getLogger(__name__)


class PortfolioExporter:
    def __init__(self, page) -> None:
        self.page = page

    def export_today(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        first_date = self.page.model_portfolio_service.get_first_trade_date(self.page.current_portfolio_id)
        if first_date is None:
            QMessageBox.information(self.page, L10N.INFO, L10N.BU_MODEL_PORTFOYDE_ISLEM_BULUNAMADI)
            return
        self._export_model_portfolio_history(first_date, date.today())

    def export_range(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        first_date = self.page.model_portfolio_service.get_first_trade_date(self.page.current_portfolio_id)
        if first_date is None:
            QMessageBox.information(self.page, L10N.INFO, L10N.BU_MODEL_PORTFOYDE_ISLEM_BULUNAMADI)
            return

        dialog = self.page.date_range_dialog_cls(self.page, min_date=first_date, max_date=date.today())
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_range()
        if not result:
            return
        start_date, end_date = result
        self._export_model_portfolio_history(start_date, end_date)

    def _export_model_portfolio_history(self, start_date: date, end_date: date) -> None:
        if self.page.current_portfolio_id is None:
            return
        portfolio = self.page.list_panel.current_portfolio()
        portfolio_name = portfolio.name if portfolio else self.page.lbl_portfolio_name.text()
        default_name = f"model_portfoy_{self._safe_file_stem(portfolio_name)}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self.page,
            L10N.MODEL_PORTFOY_RAPORU,
            default_name,
            L10N.EXCEL_DOSYALARI_XLSX,
        )
        if not file_path:
            return

        try:
            self.page.model_portfolio_excel_export_service.export_model_portfolio_history(
                portfolio_id=self.page.current_portfolio_id,
                start_date=start_date,
                end_date=end_date,
                file_path=file_path,
                mode=ExportMode.OVERWRITE,
            )
            QMessageBox.information(self.page, L10N.SUCCESS, L10N.MODEL_PORTFOY_EXCEL_RAPORU_OLUSTURULDU)
        except Exception as exc:
            QMessageBox.critical(self.page, L10N.ERROR, f"Excel raporu oluşturulamadı: {exc}")

    @staticmethod
    def _safe_file_stem(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower())
        return "_".join(part for part in cleaned.split("_") if part) or "model_portfoy"
