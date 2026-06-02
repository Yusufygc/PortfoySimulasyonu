from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.application.services.reporting.daily_history_models import SheetName
from src.application.services.reporting.excel_data_preparer import ExcelDataPreparer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExcelAppendFrames:
    summary_df: pd.DataFrame
    detail_df: pd.DataFrame
    stock_summary_df: pd.DataFrame


class ExcelAppendMerger:
    def __init__(self, data_preparer: ExcelDataPreparer) -> None:
        self._data_preparer = data_preparer

    def merge_existing(
        self,
        file_path: Path,
        summary_df: pd.DataFrame,
        detail_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
    ) -> ExcelAppendFrames | None:
        self._assert_file_writable(file_path)
        existing = self._read_existing_frames(file_path)
        if existing is None:
            return None
        existing_summary, existing_detail, existing_stock_summary = existing
        return ExcelAppendFrames(
            summary_df=self._merge_summary(existing_summary, summary_df),
            detail_df=self._merge_detail(existing_detail, detail_df),
            stock_summary_df=self._merge_stock_summary(existing_stock_summary, stock_summary_df),
        )

    def _assert_file_writable(self, file_path: Path) -> None:
        try:
            with open(file_path, "r+"):
                pass
        except PermissionError:
            raise PermissionError(
                f"Dosya şu an açık: {file_path.name}\n"
                "Lütfen Excel dosyasını kapatıp tekrar deneyin."
            )
        except FileNotFoundError:
            return
        except OSError as exc:
            logger.debug("Excel erişim ön kontrolü atlandı: %s", exc)

    def _read_existing_frames(self, file_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
        if not file_path.exists():
            return None
        try:
            with pd.ExcelFile(file_path, engine="openpyxl") as xls:
                names = xls.sheet_names
                return (
                    pd.read_excel(xls, sheet_name=SheetName.SUMMARY)
                    if SheetName.SUMMARY in names
                    else pd.DataFrame(),
                    pd.read_excel(xls, sheet_name=SheetName.DAILY_DETAIL)
                    if SheetName.DAILY_DETAIL in names
                    else pd.DataFrame(),
                    pd.read_excel(xls, sheet_name=SheetName.STOCK_SUMMARY)
                    if SheetName.STOCK_SUMMARY in names
                    else pd.DataFrame(),
                )
        except Exception as exc:
            logger.warning("Eski dosya okunamadı: %s. Dosya yedeklenip yeniden oluşturulacak.", exc)
            shutil.copy(file_path, file_path.with_suffix(file_path.suffix + ".bak"))
            return None

    def _merge_summary(self, existing_summary: pd.DataFrame, summary_df: pd.DataFrame) -> pd.DataFrame:
        combined = pd.concat([existing_summary, summary_df], ignore_index=True)
        if combined.empty or "Tarih" not in combined.columns:
            return combined
        combined = self._data_preparer.normalize_date_column(combined)
        return (
            combined
            .drop_duplicates(subset=["Tarih"], keep="last")
            .sort_values("Tarih")
            .reset_index(drop=True)
        )

    def _merge_detail(self, existing_detail: pd.DataFrame, detail_df: pd.DataFrame) -> pd.DataFrame:
        existing_detail = self._without_existing_total_rows(existing_detail)
        combined = pd.concat([existing_detail, detail_df], ignore_index=True)
        if combined.empty or "Tarih" not in combined.columns or "Hisse" not in combined.columns:
            return combined
        combined = self._data_preparer.normalize_date_column(combined)
        return (
            combined
            .drop_duplicates(subset=["Tarih", "Hisse"], keep="last")
            .sort_values(["Tarih", "Hisse"], na_position="last")
            .reset_index(drop=True)
        )

    @staticmethod
    def _without_existing_total_rows(existing_detail: pd.DataFrame) -> pd.DataFrame:
        if existing_detail.empty or "Hisse" not in existing_detail.columns:
            return existing_detail
        total_mask = existing_detail["Hisse"].str.contains("GÜNLÜK TOPLAM", na=False)
        return existing_detail[~total_mask]

    @staticmethod
    def _merge_stock_summary(
        existing_stock_summary: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
    ) -> pd.DataFrame:
        combined = pd.concat([existing_stock_summary, stock_summary_df], ignore_index=True)
        if combined.empty or "Hisse" not in combined.columns:
            return combined
        return (
            combined
            .drop_duplicates(subset=["Hisse"], keep="last")
            .sort_values("Hisse")
            .reset_index(drop=True)
        )
