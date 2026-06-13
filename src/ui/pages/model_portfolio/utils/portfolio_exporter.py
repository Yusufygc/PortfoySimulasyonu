from src.ui.shared.locale_tr import L10N
# src/ui/pages/model_portfolio/utils/portfolio_exporter.py

import logging
from datetime import date
from src.qt_compat.qtwidgets import QMessageBox, QFileDialog, QDialog

from src.application.services.market.price_data_health_service import PRICE_SCOPE_MODEL_PREFIX
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
        if dialog.exec() != QDialog.Accepted:
            return
        result = dialog.get_range()
        if not result:
            return
        start_date, end_date = result
        self._export_model_portfolio_history(start_date, end_date)

    def _export_model_portfolio_history(self, start_date: date, end_date: date) -> None:
        if self.page.current_portfolio_id is None:
            return
        if self._has_missing_history_prices(start_date, end_date):
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
            QMessageBox.critical(self.page, L10N.ERROR, L10N.EXCEL_RAPORU_OLUSTURULAMADI_TMPL.format(exc=exc))

    def _has_missing_history_prices(self, start_date: date, end_date: date) -> bool:
        health_service = getattr(self.page, "price_data_health_service", None)
        if health_service is None or self.page.current_portfolio_id is None:
            return False

        scope = f"{PRICE_SCOPE_MODEL_PREFIX}{self.page.current_portfolio_id}"
        report = health_service.analyze(start_date, end_date, scope=scope)
        if report.total_missing_count == 0:
            return False

        QMessageBox.warning(
            self.page,
            L10N.MODEL_PORTFOY_RAPORU_EKSIK_FIYAT_BASLIK,
            self._format_missing_price_message(report),
        )
        return True

    def _format_missing_price_message(self, report) -> str:
        details = []
        missing_rows = [row for row in report.rows if row.missing_dates]
        for row in missing_rows[:8]:
            dates = ", ".join(point_date.strftime(L10N.DMY) for point_date in row.missing_dates[:5])
            if row.missing_count > 5:
                dates += f", ... +{row.missing_count - 5} gün"
            details.append(f"- {row.ticker}: {dates}")
        if len(missing_rows) > 8:
            details.append(f"- ... +{len(missing_rows) - 8} hisse")

        return (
            f"{L10N.MODEL_PORTFOY_RAPORU_EKSIK_FIYAT_UYARISI}\n\n"
            + "\n".join(details)
        )

    @staticmethod
    def _safe_file_stem(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower())
        return "_".join(part for part in cleaned.split("_") if part) or "model_portfoy"
