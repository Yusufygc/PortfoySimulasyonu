from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from typing import TYPE_CHECKING

from src.qt_compat.qtcore import Qt
from src.qt_compat.qtgui import QColor
from src.qt_compat.qtwidgets import QTableWidgetItem

from src.application.services.market.price_data_health_service import PriceDataHealthReport
from src.ui.formatters import display_ticker

if TYPE_CHECKING:
    from src.ui.pages.settings.price_data_panel import PriceDataPanel


class PriceDataReportRenderer:
    """Sağlık raporu verilerini tablo ve HTML formatına dönüştürür."""

    def __init__(self, panel: PriceDataPanel) -> None:
        self.panel = panel

    def clear_report(self) -> None:
        panel = self.panel
        panel._current_report = None
        panel.health_table.setRowCount(0)
        for label in (
            panel.lbl_stock_count,
            panel.lbl_missing_count,
            panel.lbl_holiday_count,
            panel.lbl_holiday_candidate_count,
            panel.lbl_latest_date,
        ):
            label.metric_label.setText("-")
        panel.detail_text.setText(L10N.ANALIZ_SONUCU_BEKLENIYOR)
        panel._set_selected_update_button_state(False)

    def apply_report(self, report: PriceDataHealthReport) -> None:
        """Raporu özet kartlara, tabloya ve detay paneline uygular."""
        panel = self.panel
        panel._current_report = report
        panel.lbl_stock_count.metric_label.setText(str(report.total_stock_count))
        panel.lbl_missing_count.metric_label.setText(str(report.total_missing_count))
        panel.lbl_holiday_count.metric_label.setText(str(report.known_holiday_count))
        panel.lbl_holiday_candidate_count.metric_label.setText(str(report.holiday_candidate_count))
        panel.lbl_latest_date.metric_label.setText(
            report.latest_price_date.strftime("%d.%m.%Y") if report.latest_price_date else "-"
        )
        self.populate_health_table()
        panel.detail_text.setHtml(self.format_report_text(report))
        panel._set_selected_update_button_state(False)

    def populate_health_table(self) -> None:
        """Sağlık tablosunu mevcut rapor verisiyle doldurur."""
        panel = self.panel
        if panel._current_report is None:
            return
        only_problem = panel.chk_problem_only.isChecked()
        rows = [
            row for row in panel._current_report.rows
            if not only_problem or row.missing_count > 0
        ]
        panel.health_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            values = [
                display_ticker(row.ticker),
                row.last_price_date.strftime("%d.%m.%Y") if row.last_price_date else "-",
                str(row.missing_count),
                row.status,
                row.first_missing_date.strftime("%d.%m.%Y") if row.first_missing_date else "-",
                row.last_missing_date.strftime("%d.%m.%Y") if row.last_missing_date else "-",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)

                if column == 0:
                    item.setData(Qt.UserRole, row.stock_id)
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setForeground(QColor("#3b82f6"))

                if column == 3:
                    item.setForeground(QColor("#10b981" if "Sağlıklı" in value else "#ef4444"))

                if column == 2 and row.missing_count > 0:
                    item.setForeground(QColor("#ef4444"))

                panel.health_table.setItem(row_index, column, item)

    def on_health_selection_changed(self) -> None:
        """Tabloda hisse seçildiğinde detay panelini günceller."""
        panel = self.panel
        if panel._current_report is None:
            panel._set_selected_update_button_state(False)
            return
        stock_id = panel._selected_stock_id()
        if stock_id is None:
            panel._set_selected_update_button_state(False)
            return
        row = next((r for r in panel._current_report.rows if r.stock_id == stock_id), None)
        if row is None:
            panel._set_selected_update_button_state(False)
            return

        missing_text = ", ".join(d.strftime(L10N.DMY) for d in row.missing_dates[:80])
        if row.missing_count > 80:
            missing_text += f"<br>... +{row.missing_count - 80} gün"
        if not missing_text:
            missing_text = "<span style='color: #94a3b8;'>Eksik gün yok.</span>"

        known_text = ", ".join(d.strftime(L10N.DMY) for d in panel._current_report.known_holiday_dates[:60])
        if not known_text:
            known_text = "<span style='color: #94a3b8;'>Bu aralıkta kayıtlı tatil yok.</span>"

        candidate_text = ", ".join(d.strftime(L10N.DMY) for d in panel._current_report.holiday_candidate_dates[:60])
        if not candidate_text:
            candidate_text = "<span style='color: #94a3b8;'>Tatil adayı yok.</span>"

        status_color = "#10b981" if "Sağlıklı" in row.status else "#ef4444"
        last_date_str = row.last_price_date.strftime("%d.%m.%Y") if row.last_price_date else "-"

        html = f"""
        <div style='font-family: Segoe UI, Arial; line-height: 1.4;'>
            <h3 style='color: #3b82f6; margin-bottom: 4px;'>{display_ticker(row.ticker)}</h3>
            <div style='margin-bottom: 12px;'>
                <b>Durum:</b> <span style='color: {status_color};'>{row.status}</span><br>
                <b>Son Veri:</b> {last_date_str}
            </div>
            <div style='margin-bottom: 12px;'>
                <b style='color: #ef4444;'>Eksik Günler ({row.missing_count}):</b><br>
                <div style='font-size: 13px;'>{missing_text}</div>
            </div>
            <div style='margin-bottom: 10px;'>
                <b style='color: #3b82f6;'>Bilinen BIST Tatilleri ({panel._current_report.known_holiday_count}):</b><br>
                <div style='font-size: 13px;'>{known_text}</div>
            </div>
            <div>
                <b style='color: #ca8a04;'>Tatil Adayları ({panel._current_report.holiday_candidate_count}):</b><br>
                <div style='font-size: 13px;'>{candidate_text}</div>
            </div>
        </div>
        """
        panel.detail_text.setHtml(html)
        panel._set_selected_update_button_state(True)

    def format_report_text(self, report: PriceDataHealthReport) -> str:
        """Tam raporu HTML string olarak döndürür."""
        problematic = [row for row in report.rows if row.missing_count > 0]
        status_color = "#10b981" if "Sağlıklı" in report.health_label else "#ef4444"

        problematic_html = ""
        if problematic:
            for row in problematic[:20]:
                problematic_html += (
                    f"<li>{display_ticker(row.ticker)}: "
                    f"<span style='color: #ef4444;'>{row.missing_count} eksik</span></li>"
                )
            if len(problematic) > 20:
                problematic_html += f"<li>... ve {len(problematic) - 20} hisse daha</li>"
        else:
            problematic_html = "<li>Yok</li>"

        known_html = ", ".join(d.strftime("%d.%m.%Y") for d in report.known_holiday_dates[:40])
        if len(report.known_holiday_dates) > 40:
            known_html += f"<br>... +{len(report.known_holiday_dates) - 40} gün"

        candidate_html = ", ".join(d.strftime("%d.%m.%Y") for d in report.holiday_candidate_dates[:40])
        if len(report.holiday_candidate_dates) > 40:
            candidate_html += f"<br>... +{len(report.holiday_candidate_dates) - 40} gün"

        return f"""
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
                <b>Bilinen Tatil:</b> <span style='color: #3b82f6;'>{report.known_holiday_count}</span><br>
                <b>Tatil Adayı (heuristik):</b> <span style='color: #ca8a04;'>{report.holiday_candidate_count}</span>
            </div>
            <div style='margin-bottom: 12px;'>
                <b style='color: #ef4444;'>Sorunlu Hisseler:</b>
                <ul style='margin-top: 4px; padding-left: 20px;'>
                    {problematic_html}
                </ul>
            </div>
            <div style='margin-bottom: 10px;'>
                <b style='color: #3b82f6;'>Bilinen BIST Tatilleri ({report.known_holiday_count}):</b><br>
                <div style='font-size: 13px;'>{known_html or "Yok"}</div>
            </div>
            <div>
                <b style='color: #ca8a04;'>Tatil Adayları - heuristik ({report.holiday_candidate_count}):</b><br>
                <div style='font-size: 13px;'>{candidate_html or "Yok"}</div>
            </div>
        </div>
        """
