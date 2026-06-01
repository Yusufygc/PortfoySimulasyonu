# src/application/services/reporting/excel_layout_manager.py

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter

from src.application.services.reporting import excel_theme as theme
from src.application.services.reporting.daily_history_models import SheetName
from src.application.services.reporting.excel_data_preparer import ExcelDataPreparer


class ExcelLayoutManager:
    def __init__(self, data_preparer: ExcelDataPreparer) -> None:
        self.data_preparer = data_preparer

    _TAB_COLORS = {
        SheetName.DASHBOARD:     "FF0D2B6E",
        SheetName.CHARTS:        "FFF9A825",
        SheetName.SUMMARY:       "FF00897B",
        SheetName.DAILY_DETAIL:  "FF455A64",
        SheetName.STOCK_SUMMARY: "FF1565C0",
        SheetName.CHART_DATA:    "FF90A4AE",
    }

    def post_process_sheets(self, workbook) -> None:
        for sheet_name, argb in self._TAB_COLORS.items():
            if sheet_name in workbook.sheetnames:
                ws = workbook[sheet_name]
                ws.sheet_properties.tabColor = Color(rgb=argb)
                if sheet_name != SheetName.CHART_DATA:
                    ws.page_setup.orientation = "landscape"
                    ws.page_setup.fitToPage = True
                    ws.page_setup.fitToWidth = 1
                    ws.page_setup.fitToHeight = 0
                    ws.oddFooter.center.text = (
                        "&İ Gizli — Yalnızca İç Kullanım &İ"
                        "        &Sayfa &S / &N"
                    )

    def style_dashboard_kpi(self, worksheet, dashboard_df: pd.DataFrame) -> None:
        if dashboard_df.empty:
            return
        kpi_rows = len(dashboard_df)
        for row_idx in range(2, kpi_rows + 2):
            worksheet.row_dimensions[row_idx].height = 28
            label_cell = worksheet.cell(row=row_idx, column=1)
            value_cell = worksheet.cell(row=row_idx, column=2)
            label_cell.font = Font(bold=True, color=theme.NAVY_PRIMARY, size=10)
            label_val = str(value_cell.value) if value_cell.value is not None else ""
            is_negative = "-" in label_val or "−" in label_val
            is_positive = not is_negative and any(c.isdigit() for c in label_val)
            if "K/Z" in str(label_cell.value or "") or "Getiri" in str(label_cell.value or ""):
                if is_negative:
                    value_cell.fill = PatternFill(start_color=theme.NEGATIVE_FILL, end_color=theme.NEGATIVE_FILL, fill_type="solid")
                    value_cell.font = Font(bold=True, color=theme.NEGATIVE_FONT, size=13)
                elif is_positive:
                    value_cell.fill = PatternFill(start_color=theme.POSITIVE_FILL, end_color=theme.POSITIVE_FILL, fill_type="solid")
                    value_cell.font = Font(bold=True, color=theme.POSITIVE_FONT, size=13)
                else:
                    value_cell.font = Font(bold=True, size=13)
            else:
                value_cell.font = Font(bold=True, color=theme.NAVY_DEEP, size=13)

    def add_banner_to_data_sheet(self, worksheet, title: str, ncols: int) -> None:
        if ncols <= 0:
            return
        worksheet.insert_rows(1)
        last_col = get_column_letter(max(ncols, 1))
        worksheet.merge_cells(f"A1:{last_col}1")
        banner = worksheet["A1"]
        banner.value = title
        banner.font = Font(bold=True, color=theme.WHITE, size=13)
        banner.fill = PatternFill(start_color=theme.NAVY_PRIMARY, end_color=theme.NAVY_PRIMARY, fill_type="solid")
        banner.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.row_dimensions[1].height = 26
        worksheet.freeze_panes = "A3"
        worksheet.auto_filter.ref = f"A2:{last_col}2"

    def style_dashboard_sheet(self, worksheet) -> None:
        worksheet.sheet_view.showGridLines = False
        worksheet.freeze_panes = "A4"
        worksheet.column_dimensions["A"].width = 22
        worksheet.column_dimensions["B"].width = 18
        worksheet.column_dimensions["C"].width = 13
        for column_idx in range(4, 24):
            worksheet.column_dimensions[get_column_letter(column_idx)].width = 13

        worksheet.insert_rows(1, 3)
        worksheet.merge_cells("A1:W1")
        title_cell = worksheet["A1"]
        title_cell.value = "Portföy Performans Paneli"
        title_cell.font = Font(bold=True, color="FFFFFF", size=16)
        title_cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.row_dimensions[1].height = 28

        worksheet.merge_cells("A2:W2")
        note_cell = worksheet["A2"]
        note_cell.value = "BIST kapalı günleri ve fiyat verisi olmayan günler performans serisine dahil edilmez."
        note_cell.font = Font(italic=True, color="666666", size=9)
        note_cell.alignment = Alignment(horizontal="center", wrap_text=True, vertical="center")
        worksheet.row_dimensions[2].height = 24

        for row in range(4, max(worksheet.max_row + 1, 62)):
            worksheet.row_dimensions[row].height = 22
        worksheet.auto_filter.ref = f"A4:B{worksheet.max_row}"

    def write_dashboard_summaries(
        self,
        worksheet,
        summary_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
    ) -> None:
        stats = self.data_preparer.dashboard_stats(summary_df, stock_summary_df)
        self._section_title(worksheet, "D4:K4", "Dönem ve Performans Özeti")
        for row_idx, (label, value) in enumerate(stats["rows"], start=5):
            worksheet.cell(row=row_idx, column=4, value=label)
            worksheet.cell(row=row_idx, column=5, value=value)
        self._style_label_value_range(worksheet, 5, 11, 4, 5)

        self._section_title(worksheet, "N4:W4", "Grafiklerden Çıkan Sonuç")
        narratives = [
            stats["portfolio_sentence"],
            stats["return_sentence"],
            stats["allocation_sentence"],
            f"Grafiklerde tarih eksen {stats['period']} dönemini kapsar; yoğun günler metin özetinde net tarihlerle açıklanır.",
        ]
        for row_idx, text in enumerate(narratives, start=5):
            worksheet.merge_cells(start_row=row_idx, start_column=14, end_row=row_idx, end_column=23)
            cell = worksheet.cell(row=row_idx, column=14, value=text)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.font = Font(color="333333", size=10)
            worksheet.row_dimensions[row_idx].height = 34

        self._section_title(worksheet, "A13:C13", "Hisse Ağırlığı İlk 3")
        headers = ["Hisse", "Değer", "Ağırlık"]
        for col_offset, header in enumerate(headers, start=1):
            worksheet.cell(row=14, column=col_offset, value=header)
        for row_offset, holding in enumerate(stats["top_holdings"], start=15):
            worksheet.cell(row=row_offset, column=1, value=holding["ticker"])
            worksheet.cell(row=row_offset, column=2, value=self.data_preparer._fmt_tl(holding["value"]))
            worksheet.cell(row=row_offset, column=3, value=self.data_preparer._fmt_pct_value(holding["weight"]))
        self._style_table_range(worksheet, 14, 18, 1, 3)

    def _section_title(self, worksheet, cell_range: str, title: str) -> None:
        worksheet.merge_cells(cell_range)
        cell = worksheet[cell_range.split(":")[0]]
        cell.value = title
        cell.fill = PatternFill(start_color="D9EAF7", end_color="D9EAF7", fill_type="solid")
        cell.font = Font(bold=True, color="1F4E78", size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    def _style_label_value_range(self, worksheet, min_row: int, max_row: int, min_col: int, max_col: int) -> None:
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                cell = worksheet.cell(row=row, column=col)
                cell.alignment = Alignment(wrap_text=True, vertical="center")
                cell.border = self._thin_border()
                if col == min_col:
                    cell.font = Font(bold=True, color="444444")

    def _style_table_range(self, worksheet, min_row: int, max_row: int, min_col: int, max_col: int) -> None:
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                cell = worksheet.cell(row=row, column=col)
                cell.alignment = Alignment(wrap_text=True, vertical="center")
                cell.border = self._thin_border()
                if row == min_row:
                    cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                    cell.font = Font(bold=True, color="FFFFFF", size=10)

    @staticmethod
    def _thin_border() -> Border:
        side = Side(style="thin", color="D9E2F3")
        return Border(left=side, right=side, top=side, bottom=side)
