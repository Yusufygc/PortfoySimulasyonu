# src/application/services/reporting/excel_report_builder.py

import logging
from pathlib import Path
from typing import List

import pandas as pd

from src.application.services.reporting.excel_append_merger import ExcelAppendMerger
from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.daily_history_models import (
    DailyPosition,
    DailyPortfolioSnapshot,
    ExportMode,
    SheetName,
)
from src.application.services.reporting.excel_data_preparer import ExcelDataPreparer
from src.application.services.reporting.excel_layout_manager import ExcelLayoutManager

logger = logging.getLogger(__name__)


class ExcelReportBuilder:
    def __init__(self, formatter: ExcelFormatter) -> None:
        self.formatter = formatter
        self.data_preparer = ExcelDataPreparer()
        self.append_merger = ExcelAppendMerger(self.data_preparer)
        self.layout_manager = ExcelLayoutManager(self.data_preparer)

    @staticmethod
    def normalize_date_column(df: pd.DataFrame, column: str = "Tarih") -> pd.DataFrame:
        return ExcelDataPreparer.normalize_date_column(df, column)

    def build_and_save(
        self,
        file_path: Path,
        daily_positions: List[DailyPosition],
        daily_snapshots: List[DailyPortfolioSnapshot],
        mode: ExportMode,
    ) -> None:
        detail_df = self.data_preparer.build_detail_df(daily_positions, daily_snapshots)
        summary_df = self.data_preparer.build_summary_df(daily_snapshots)
        stock_summary_df = self.data_preparer.build_stock_summary_df(daily_positions)
        dashboard_df = self.data_preparer.build_dashboard_df(daily_snapshots, daily_positions)

        if file_path.exists() and mode != ExportMode.OVERWRITE:
            merged = self.append_merger.merge_existing(
                file_path=file_path,
                summary_df=summary_df,
                detail_df=detail_df,
                stock_summary_df=stock_summary_df,
            )
            if merged is not None:
                summary_df = merged.summary_df
                detail_df = merged.detail_df
                stock_summary_df = merged.stock_summary_df

        self._write_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)

    # ────── Backward Compatibility Wrappers for Tests/Internal Calls ──────
    def _build_summary_df(self, snapshots):
        return self.data_preparer.build_summary_df(snapshots)

    def _build_detail_df(self, positions, snapshots):
        return self.data_preparer.build_detail_df(positions, snapshots)

    def _build_stock_summary_df(self, positions):
        return self.data_preparer.build_stock_summary_df(positions)

    def _build_dashboard_df(self, snapshots, positions):
        return self.data_preparer.build_dashboard_df(snapshots, positions)

    def _fmt_tr_money(self, val):
        return self.data_preparer._fmt_tr_money(val)

    def _write_excel(
        self,
        file_path: Path,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
        dashboard_df: pd.DataFrame,
    ) -> None:
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                dashboard_df.to_excel(writer,     sheet_name=SheetName.DASHBOARD,     index=False)
                summary_df.to_excel(writer,       sheet_name=SheetName.SUMMARY,       index=False)
                detail_df.to_excel(writer,        sheet_name=SheetName.DAILY_DETAIL,  index=False)
                stock_summary_df.to_excel(writer, sheet_name=SheetName.STOCK_SUMMARY, index=False)

                self.formatter.apply_formatting(writer, SheetName.DASHBOARD,     dashboard_df)
                self.formatter.apply_formatting(writer, SheetName.SUMMARY,       summary_df)
                self.formatter.apply_formatting(writer, SheetName.DAILY_DETAIL,  detail_df)
                self.formatter.apply_formatting(writer, SheetName.STOCK_SUMMARY, stock_summary_df)
                
                self.layout_manager.style_dashboard_kpi(writer.sheets[SheetName.DASHBOARD], dashboard_df)
                self.layout_manager.add_banner_to_data_sheet(writer.sheets[SheetName.SUMMARY],       "Portföy Özeti",     len(summary_df.columns))
                self.layout_manager.add_banner_to_data_sheet(writer.sheets[SheetName.DAILY_DETAIL],  "Günlük Detaylar",   len(detail_df.columns))
                self.layout_manager.add_banner_to_data_sheet(writer.sheets[SheetName.STOCK_SUMMARY], "Hisse Özeti",       len(stock_summary_df.columns))
                
                self.layout_manager.post_process_sheets(writer.book)
        except PermissionError:
            raise PermissionError(
                f"Dosyaya yazılamadı: {file_path}\n"
                "Dosya açık olabilir. Lütfen kapatıp tekrar deneyin."
            )

