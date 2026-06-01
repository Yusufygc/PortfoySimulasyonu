# src/application/services/reporting/excel_report_builder.py

import logging
import shutil
from pathlib import Path
from typing import List

import pandas as pd

from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.daily_history_models import (
    DailyPosition,
    DailyPortfolioSnapshot,
    ExportMode,
    SheetName,
)
from src.application.services.reporting.excel_data_preparer import ExcelDataPreparer
from src.application.services.reporting.excel_chart_builder import ExcelChartBuilder
from src.application.services.reporting.excel_layout_manager import ExcelLayoutManager

logger = logging.getLogger(__name__)


class ExcelReportBuilder:
    def __init__(self, formatter: ExcelFormatter) -> None:
        self.formatter = formatter
        self.data_preparer = ExcelDataPreparer()
        self.chart_builder = ExcelChartBuilder(self.data_preparer)
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

        if not file_path.exists() or mode == ExportMode.OVERWRITE:
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)
        else:
            self._append_to_existing_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)

    # ────── Backward Compatibility Wrappers for Tests/Internal Calls ──────
    def _build_summary_df(self, snapshots):
        return self.data_preparer.build_summary_df(snapshots)

    def _build_detail_df(self, positions, snapshots):
        return self.data_preparer.build_detail_df(positions, snapshots)

    def _build_stock_summary_df(self, positions):
        return self.data_preparer.build_stock_summary_df(positions)

    def _build_dashboard_df(self, snapshots, positions):
        return self.data_preparer.build_dashboard_df(snapshots, positions)

    def _build_chart_data_df(self, summary_df):
        return self.data_preparer.build_chart_data_df(summary_df)

    def _fmt_tr_money(self, val):
        return self.data_preparer._fmt_tr_money(val)

    def _write_fresh_excel(
        self,
        file_path: Path,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
        dashboard_df: pd.DataFrame,
    ) -> None:
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                chart_data_df = self.data_preparer.build_chart_data_df(summary_df)
                dashboard_df.to_excel(writer,     sheet_name=SheetName.DASHBOARD,     index=False)
                summary_df.to_excel(writer,       sheet_name=SheetName.SUMMARY,       index=False)
                detail_df.to_excel(writer,        sheet_name=SheetName.DAILY_DETAIL,  index=False)
                stock_summary_df.to_excel(writer, sheet_name=SheetName.STOCK_SUMMARY, index=False)
                pd.DataFrame().to_excel(writer,   sheet_name=SheetName.CHARTS,        index=False)
                chart_data_df.to_excel(writer,    sheet_name=SheetName.CHART_DATA,    index=False)
                writer.sheets[SheetName.CHART_DATA].sheet_state = "hidden"

                self.formatter.apply_formatting(writer, SheetName.DASHBOARD,     dashboard_df)
                self.formatter.apply_formatting(writer, SheetName.SUMMARY,       summary_df)
                self.formatter.apply_formatting(writer, SheetName.DAILY_DETAIL,  detail_df)
                self.formatter.apply_formatting(writer, SheetName.STOCK_SUMMARY, stock_summary_df)
                
                self.chart_builder.add_charts_sheet(writer, summary_df, stock_summary_df)
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

    def _append_to_existing_excel(
        self,
        file_path: Path,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
        dashboard_df: pd.DataFrame,
    ) -> None:
        try:
            with open(file_path, "r+"):
                pass
        except PermissionError:
            raise PermissionError(
                f"Dosya şu an açık: {file_path.name}\n"
                "Lütfen Excel dosyasını kapatıp tekrar deneyin."
            )
        except Exception:
            pass

        try:
            with pd.ExcelFile(file_path, engine="openpyxl") as xls:
                names = xls.sheet_names
                existing_summary   = pd.read_excel(xls, sheet_name=SheetName.SUMMARY)       if SheetName.SUMMARY       in names else pd.DataFrame()
                existing_detail    = pd.read_excel(xls, sheet_name=SheetName.DAILY_DETAIL)  if SheetName.DAILY_DETAIL  in names else pd.DataFrame()
                existing_stock_sum = pd.read_excel(xls, sheet_name=SheetName.STOCK_SUMMARY) if SheetName.STOCK_SUMMARY in names else pd.DataFrame()
        except Exception as e:
            logger.warning("Eski dosya okunamadı: %s. Dosya yedeklenip yeniden oluşturulacak.", e)
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy(file_path, backup_path)
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)
            return

        # ── Summary dedup ─────────────────────────────────────────────────────
        combined_summary = pd.concat([existing_summary, summary_df], ignore_index=True)
        if not combined_summary.empty and "Tarih" in combined_summary.columns:
            combined_summary = self.data_preparer.normalize_date_column(combined_summary)
            combined_summary = (
                combined_summary
                .drop_duplicates(subset=["Tarih"], keep="last")
                .sort_values("Tarih")
                .reset_index(drop=True)
            )

        # ── Detail dedup — TOPLAM satırları Tarih=None olduğundan önceden temizlenir ──
        if not existing_detail.empty and "Hisse" in existing_detail.columns:
            toplam_mask = existing_detail["Hisse"].str.contains("GÜNLÜK TOPLAM", na=False)
            existing_detail = existing_detail[~toplam_mask]

        combined_detail = pd.concat([existing_detail, detail_df], ignore_index=True)
        if not combined_detail.empty and "Tarih" in combined_detail.columns and "Hisse" in combined_detail.columns:
            combined_detail = self.data_preparer.normalize_date_column(combined_detail)
            combined_detail = (
                combined_detail
                .drop_duplicates(subset=["Tarih", "Hisse"], keep="last")
                .sort_values(["Tarih", "Hisse"], na_position="last")
                .reset_index(drop=True)
            )

        # ── Stock summary dedup ───────────────────────────────────────────────
        combined_stock_sum = pd.concat([existing_stock_sum, stock_summary_df], ignore_index=True)
        if not combined_stock_sum.empty and "Hisse" in combined_stock_sum.columns:
            combined_stock_sum = (
                combined_stock_sum
                .drop_duplicates(subset=["Hisse"], keep="last")
                .sort_values("Hisse")
                .reset_index(drop=True)
            )

        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                chart_data_df = self.data_preparer.build_chart_data_df(combined_summary)
                dashboard_df.to_excel(writer,       sheet_name=SheetName.DASHBOARD,     index=False)
                combined_summary.to_excel(writer,   sheet_name=SheetName.SUMMARY,       index=False)
                combined_detail.to_excel(writer,    sheet_name=SheetName.DAILY_DETAIL,  index=False)
                combined_stock_sum.to_excel(writer, sheet_name=SheetName.STOCK_SUMMARY, index=False)
                pd.DataFrame().to_excel(writer,     sheet_name=SheetName.CHARTS,        index=False)
                chart_data_df.to_excel(writer,      sheet_name=SheetName.CHART_DATA,    index=False)
                writer.sheets[SheetName.CHART_DATA].sheet_state = "hidden"

                self.formatter.apply_formatting(writer, SheetName.DASHBOARD,     dashboard_df)
                self.formatter.apply_formatting(writer, SheetName.SUMMARY,       combined_summary)
                self.formatter.apply_formatting(writer, SheetName.DAILY_DETAIL,  combined_detail)
                self.formatter.apply_formatting(writer, SheetName.STOCK_SUMMARY, combined_stock_sum)
                
                self.chart_builder.add_charts_sheet(writer, combined_summary, combined_stock_sum)
                self.layout_manager.style_dashboard_kpi(writer.sheets[SheetName.DASHBOARD], dashboard_df)
                self.layout_manager.add_banner_to_data_sheet(writer.sheets[SheetName.SUMMARY],       "Portföy Özeti",     len(combined_summary.columns))
                self.layout_manager.add_banner_to_data_sheet(writer.sheets[SheetName.DAILY_DETAIL],  "Günlük Detaylar",   len(combined_detail.columns))
                self.layout_manager.add_banner_to_data_sheet(writer.sheets[SheetName.STOCK_SUMMARY], "Hisse Özeti",       len(combined_stock_sum.columns))
                self.layout_manager.post_process_sheets(writer.book)
        except PermissionError:
            raise PermissionError(
                f"Dosyaya yazılamadı: {file_path}\n"
                "Dosya açık olabilir. Lütfen kapatıp tekrar deneyin."
            )
