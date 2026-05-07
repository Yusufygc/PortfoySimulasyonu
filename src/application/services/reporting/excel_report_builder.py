# src/application/services/excel_report_builder.py

import logging
import shutil
from decimal import Decimal
from pathlib import Path
from typing import List, Iterable, Optional

import pandas as pd

from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.daily_history_models import (
    DailyPosition,
    DailyPortfolioSnapshot,
    ExportMode,
    PortfolioStatus,
    SheetName,
    SUMMARY_ROW_LABEL,
)

logger = logging.getLogger(__name__)


def _sf(val: Optional[Decimal]) -> Optional[float]:
    """Decimal → float; None ve Decimal("0") her ikisi de doğru işlenir."""
    return float(val) if val is not None else None


class ExcelReportBuilder:
    def __init__(self, formatter: ExcelFormatter) -> None:
        self.formatter = formatter

    def build_and_save(
        self,
        file_path: Path,
        daily_positions: List[DailyPosition],
        daily_snapshots: List[DailyPortfolioSnapshot],
        mode: ExportMode,
    ) -> None:
        detail_df       = self._build_detail_df(daily_positions, daily_snapshots)
        summary_df      = self._build_summary_df(daily_snapshots)
        stock_summary_df = self._build_stock_summary_df(daily_positions)
        dashboard_df    = self._build_dashboard_df(daily_snapshots, daily_positions)

        if not file_path.exists() or mode == ExportMode.OVERWRITE:
            self._write_fresh_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)
        else:
            self._append_to_existing_excel(file_path, summary_df, detail_df, stock_summary_df, dashboard_df)

    def _format_pct(self, value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None

    def _build_dashboard_df(
        self,
        snapshots: List[DailyPortfolioSnapshot],
        positions: List[DailyPosition],
    ) -> pd.DataFrame:
        if not snapshots:
            return pd.DataFrame()

        latest_snapshot = snapshots[-1]
        latest_date = latest_snapshot.date
        latest_positions = {p.ticker: p for p in positions if p.date == latest_date}

        best_stock  = max(
            latest_positions.values(),
            key=lambda p: p.unrealized_pnl_pct if p.unrealized_pnl_pct is not None else Decimal("-inf"),
            default=None,
        )
        worst_stock = min(
            latest_positions.values(),
            key=lambda p: p.unrealized_pnl_pct if p.unrealized_pnl_pct is not None else Decimal("inf"),
            default=None,
        )

        records = [
            {"Metrik": "Toplam Maliyet",           "Değer": self._fmt_tr_money(latest_snapshot.total_cost_basis)},
            {"Metrik": "Güncel Portföy Değeri",     "Değer": self._fmt_tr_money(latest_snapshot.total_value)},
            {"Metrik": "Toplam Kâr/Zarar (TL)",    "Değer": self._fmt_tr_money(latest_snapshot.cumulative_pnl)},
            {"Metrik": "Toplam Getiri (%)",         "Değer": self._fmt_tr_pct(latest_snapshot.cumulative_return_pct)},
        ]

        if best_stock:
            pct_str = f"{float(best_stock.unrealized_pnl_pct * 100):.2f}%" if best_stock.unrealized_pnl_pct is not None else "N/A"
            records.append({"Metrik": "En İyi Performans",  "Değer": f"{best_stock.ticker} ({pct_str})"})
        if worst_stock:
            pct_str = f"{float(worst_stock.unrealized_pnl_pct * 100):.2f}%" if worst_stock.unrealized_pnl_pct is not None else "N/A"
            records.append({"Metrik": "En Kötü Performans", "Değer": f"{worst_stock.ticker} ({pct_str})"})

        return pd.DataFrame(records)

    def _fmt_tr_money(self, val: Optional[Decimal]) -> str:
        if val is None:
            return "—"
        s = f"{val:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _fmt_tr_pct(self, val: Optional[Decimal]) -> str:
        if val is None:
            return "—"
        s = f"{val * 100:.2f}"
        return f"%{s.replace('.', ',')}"

    def _build_detail_df(
        self,
        positions: Iterable[DailyPosition],
        snapshots: Iterable[DailyPortfolioSnapshot],
    ) -> pd.DataFrame:
        snapshot_map = {s.date: s for s in snapshots}
        positions_by_date: dict = {}
        for p in positions:
            positions_by_date.setdefault(p.date, []).append(p)

        records = []
        for d in sorted(positions_by_date):
            day_positions = sorted(positions_by_date[d], key=lambda x: x.ticker)

            total_cost_basis       = Decimal("0")
            total_position_value   = Decimal("0")
            total_unrealized_pnl   = Decimal("0")

            for p in day_positions:
                records.append({
                    "Tarih":                  p.date,
                    "Hisse":                  p.ticker,
                    "Adet":                   p.quantity,
                    "Ort. Maliyet (TL)":      float(p.avg_cost),
                    "Güncel Fiyat (TL)":      _sf(p.close_price),
                    "Toplam Maliyet (TL)":    float(p.cost_basis),
                    "Pozisyon Değeri (TL)":   _sf(p.position_value),
                    "Günlük Fiyat Değ. (%)":  self._format_pct(p.daily_price_change_pct),
                    "Günlük K/Z (TL)":        _sf(p.daily_pnl_tl),
                    "Toplam K/Z (TL)":        _sf(p.unrealized_pnl_tl),
                    "Toplam K/Z (%)":         self._format_pct(p.unrealized_pnl_pct),
                    "Portföy Ağırlığı (%)":   self._format_pct(p.weight_pct),
                })

                total_cost_basis     += p.cost_basis
                if p.position_value is not None:
                    total_position_value += p.position_value
                if p.unrealized_pnl_tl is not None:
                    total_unrealized_pnl += p.unrealized_pnl_tl

            snapshot = snapshot_map.get(d)
            total_unrealized_ratio = (
                total_unrealized_pnl / total_cost_basis
                if total_cost_basis != 0 else None
            )

            records.append({
                "Tarih":                  None,
                "Hisse":                  SUMMARY_ROW_LABEL,
                "Adet":                   None,
                "Ort. Maliyet (TL)":      None,
                "Güncel Fiyat (TL)":      None,
                "Toplam Maliyet (TL)":    float(total_cost_basis),
                "Pozisyon Değeri (TL)":   float(total_position_value),
                "Günlük Fiyat Değ. (%)":  self._format_pct(snapshot.daily_return_pct if snapshot else None),
                "Günlük K/Z (TL)":        _sf(snapshot.daily_pnl if snapshot else None),
                "Toplam K/Z (TL)":        float(total_unrealized_pnl),
                "Toplam K/Z (%)":         self._format_pct(total_unrealized_ratio),
                "Portföy Ağırlığı (%)":   self._format_pct(Decimal("1.0")),
            })

        return pd.DataFrame.from_records(records)

    def _build_stock_summary_df(self, positions: List[DailyPosition]) -> pd.DataFrame:
        if not positions:
            return pd.DataFrame()

        latest_positions: dict = {}
        stock_days_count: dict = {}
        for p in positions:
            latest_positions[p.ticker] = p
            stock_days_count[p.ticker] = stock_days_count.get(p.ticker, 0) + 1

        records = []
        for ticker, p in latest_positions.items():
            records.append({
                "Hisse":                    ticker,
                "Son Adet":                 p.quantity,
                "Ort. Maliyet (TL)":        float(p.avg_cost),
                "Son Fiyat (TL)":           _sf(p.close_price),
                "Son Pozisyon Değeri (TL)": _sf(p.position_value),
                "K/Z (TL)":                 _sf(p.unrealized_pnl_tl),
                "K/Z (%)":                  self._format_pct(p.unrealized_pnl_pct),
                "Toplam Gün Sayısı":        stock_days_count[ticker],
            })

        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Hisse").reset_index(drop=True)
        return df

    def _build_summary_df(self, snapshots: Iterable[DailyPortfolioSnapshot]) -> pd.DataFrame:
        records = []
        for s in snapshots:
            if s.status == PortfolioStatus.WEEKEND:
                continue
            records.append({
                "Tarih":              s.date,
                "Portföy Değeri (TL)": _sf(s.total_value),
                "Günlük Getiri (%)":   self._format_pct(s.daily_return_pct),
                "Toplam Getiri (%)":   self._format_pct(s.cumulative_return_pct),
                "Günlük K/Z (TL)":    _sf(s.daily_pnl),
                "Toplam K/Z (TL)":    _sf(s.cumulative_pnl),
            })
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Tarih").reset_index(drop=True)
        return df

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
                dashboard_df.to_excel(writer,     sheet_name=SheetName.DASHBOARD,     index=False)
                summary_df.to_excel(writer,       sheet_name=SheetName.SUMMARY,       index=False)
                detail_df.to_excel(writer,        sheet_name=SheetName.DAILY_DETAIL,  index=False)
                stock_summary_df.to_excel(writer, sheet_name=SheetName.STOCK_SUMMARY, index=False)

                self.formatter.apply_formatting(writer, SheetName.DASHBOARD,     dashboard_df)
                self.formatter.apply_formatting(writer, SheetName.SUMMARY,       summary_df)
                self.formatter.apply_formatting(writer, SheetName.DAILY_DETAIL,  detail_df)
                self.formatter.apply_formatting(writer, SheetName.STOCK_SUMMARY, stock_summary_df)
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
            combined_detail = (
                combined_detail
                .drop_duplicates(subset=["Tarih", "Hisse"], keep="last")
                .sort_values(["Tarih", "Hisse"])
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
                dashboard_df.to_excel(writer,       sheet_name=SheetName.DASHBOARD,     index=False)
                combined_summary.to_excel(writer,   sheet_name=SheetName.SUMMARY,       index=False)
                combined_detail.to_excel(writer,    sheet_name=SheetName.DAILY_DETAIL,  index=False)
                combined_stock_sum.to_excel(writer, sheet_name=SheetName.STOCK_SUMMARY, index=False)

                self.formatter.apply_formatting(writer, SheetName.DASHBOARD,     dashboard_df)
                self.formatter.apply_formatting(writer, SheetName.SUMMARY,       combined_summary)
                self.formatter.apply_formatting(writer, SheetName.DAILY_DETAIL,  combined_detail)
                self.formatter.apply_formatting(writer, SheetName.STOCK_SUMMARY, combined_stock_sum)
        except PermissionError:
            raise PermissionError(
                f"Dosyaya yazılamadı: {file_path}\n"
                "Dosya açık olabilir. Lütfen kapatıp tekrar deneyin."
            )
