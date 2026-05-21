# src/application/services/excel_report_builder.py

import logging
import shutil
from decimal import Decimal
from pathlib import Path
from typing import List, Iterable, Optional

import pandas as pd
from openpyxl.chart import AreaChart, BarChart, DoughnutChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter

from src.application.services.reporting import excel_theme as theme
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

    @staticmethod
    def normalize_date_column(df: pd.DataFrame, column: str = "Tarih") -> pd.DataFrame:
        if df.empty or column not in df.columns:
            return df

        normalized_df = df.copy()
        normalized_dates = pd.to_datetime(normalized_df[column], errors="coerce")
        normalized_df[column] = normalized_dates.dt.date
        normalized_df.loc[normalized_dates.isna(), column] = None
        return normalized_df

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

        latest_snapshot = next(
            (snapshot for snapshot in reversed(snapshots) if snapshot.status == PortfolioStatus.OPEN),
            snapshots[-1],
        )
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

    @staticmethod
    def _num(value) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _fmt_date(value) -> str:
        if pd.isna(value):
            return "—"
        return pd.to_datetime(value).strftime("%d.%m.%Y")

    def _fmt_tl(self, value: float | None) -> str:
        if value is None:
            return "—"
        s = f"{value:,.2f}"
        return f"{s.replace(',', 'X').replace('.', ',').replace('X', '.')} TL"

    @staticmethod
    def _fmt_pct_value(value: float | None) -> str:
        if value is None:
            return "—"
        return f"%{value * 100:.2f}".replace(".", ",")

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
            if s.status != PortfolioStatus.OPEN:
                continue
            records.append({
                "Tarih":              s.date,
                "Portföy Değeri (TL)": _sf(s.total_value),
                "Günlük Getiri (%)":   self._format_pct(s.daily_return_pct),
                "Toplam Getiri (%)":   self._format_pct(s.cumulative_return_pct),
                "Günlük K/Z (TL)":    _sf(s.daily_pnl),
                "Toplam K/Z (TL)":    _sf(s.cumulative_pnl),
                "Toplam Maliyet (TL)": _sf(s.total_cost_basis),
            })
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            df = df.sort_values("Tarih").reset_index(drop=True)
        return df

    def _build_chart_data_df(self, summary_df: pd.DataFrame) -> pd.DataFrame:
        if summary_df.empty:
            return pd.DataFrame()

        base_cols = ["Tarih", "Portföy Değeri (TL)", "Günlük Getiri (%)", "Toplam Getiri (%)"]
        chart_df = summary_df[[c for c in base_cols if c in summary_df.columns]].copy()
        daily_return = pd.to_numeric(chart_df["Günlük Getiri (%)"], errors="coerce")
        chart_df["Pozitif Günlük Getiri (%)"] = daily_return.where(daily_return >= 0)
        chart_df["Negatif Günlük Getiri (%)"] = daily_return.where(daily_return < 0)

        value = pd.to_numeric(chart_df["Portföy Değeri (TL)"], errors="coerce")
        running_peak = value.cummax()
        drawdown = (value - running_peak) / running_peak.where(running_peak != 0)
        chart_df["Drawdown (%)"] = drawdown.where(drawdown.notna(), 0).clip(upper=0)

        cost_basis_col = "Toplam Maliyet (TL)"
        if cost_basis_col in summary_df.columns:
            chart_df[cost_basis_col] = pd.to_numeric(summary_df[cost_basis_col], errors="coerce")
        else:
            chart_df[cost_basis_col] = None

        return chart_df[[
            "Tarih",
            "Portföy Değeri (TL)",
            "Pozitif Günlük Getiri (%)",
            "Negatif Günlük Getiri (%)",
            "Toplam Getiri (%)",
            "Drawdown (%)",
            cost_basis_col,
        ]]

    def _dashboard_stats(self, summary_df: pd.DataFrame, stock_summary_df: pd.DataFrame) -> dict:
        stats = {
            "period": "Veri yok",
            "portfolio_sentence": "Portföy değeri grafiği için yeterli veri yok.",
            "return_sentence": "Getiri grafikleri için yeterli veri yok.",
            "allocation_sentence": "Hisse dağılımı için yeterli veri yok.",
            "rows": [],
            "top_holdings": [],
        }
        if not summary_df.empty:
            df = summary_df.copy()
            df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
            df = df.dropna(subset=["Tarih"]).reset_index(drop=True)
            if not df.empty:
                first = df.iloc[0]
                last = df.iloc[-1]
                start_value = self._num(first.get("Portföy Değeri (TL)"))
                end_value = self._num(last.get("Portföy Değeri (TL)"))
                change_tl = end_value - start_value if start_value is not None and end_value is not None else None
                change_pct = change_tl / start_value if change_tl is not None and start_value else None

                value_series = pd.to_numeric(df["Portföy Değeri (TL)"], errors="coerce")
                peak_idx = value_series.idxmax() if value_series.notna().any() else None
                low_idx = value_series.idxmin() if value_series.notna().any() else None
                peak = df.loc[peak_idx] if peak_idx is not None else None
                low = df.loc[low_idx] if low_idx is not None else None

                daily_series = pd.to_numeric(df["Günlük Getiri (%)"], errors="coerce")
                best_idx = daily_series.idxmax() if daily_series.notna().any() else None
                worst_idx = daily_series.idxmin() if daily_series.notna().any() else None
                best = df.loc[best_idx] if best_idx is not None else None
                worst = df.loc[worst_idx] if worst_idx is not None else None

                stats["period"] = f"{self._fmt_date(first['Tarih'])} - {self._fmt_date(last['Tarih'])}"
                stats["rows"] = [
                    ("Rapor dönemi", stats["period"]),
                    ("Başlangıç değeri", self._fmt_tl(start_value)),
                    ("Bitiş değeri", self._fmt_tl(end_value)),
                    ("Dönem değişimi", f"{self._fmt_tl(change_tl)} / {self._fmt_pct_value(change_pct)}"),
                    (
                        "En yüksek değer",
                        f"{self._fmt_tl(self._num(peak['Portföy Değeri (TL)']))} ({self._fmt_date(peak['Tarih'])})" if peak is not None else "—",
                    ),
                    (
                        "En düşük değer",
                        f"{self._fmt_tl(self._num(low['Portföy Değeri (TL)']))} ({self._fmt_date(low['Tarih'])})" if low is not None else "—",
                    ),
                    ("Dönem sonu getiri", self._fmt_pct_value(self._num(last.get("Toplam Getiri (%)")))),
                ]
                stats["portfolio_sentence"] = (
                    f"Portföy {stats['period']} döneminde {self._fmt_tl(start_value)} seviyesinden "
                    f"{self._fmt_tl(end_value)} seviyesine geldi. Net değişim {self._fmt_tl(change_tl)} "
                    f"({self._fmt_pct_value(change_pct)})."
                )
                stats["return_sentence"] = (
                    f"En iyi günlük getiri {self._fmt_date(best['Tarih'])} tarihinde "
                    f"{self._fmt_pct_value(self._num(best['Günlük Getiri (%)']))}; en kötü günlük getiri "
                    f"{self._fmt_date(worst['Tarih'])} tarihinde {self._fmt_pct_value(self._num(worst['Günlük Getiri (%)']))}."
                    if best is not None and worst is not None
                    else stats["return_sentence"]
                )

        holdings = self._top_holdings(stock_summary_df)
        if holdings:
            stats["top_holdings"] = holdings
            leader = holdings[0]
            stats["allocation_sentence"] = (
                f"En büyük ağırlık {leader['ticker']} hissesinde: "
                f"{self._fmt_tl(leader['value'])} ({self._fmt_pct_value(leader['weight'])})."
            )
        return stats

    def _top_holdings(self, stock_summary_df: pd.DataFrame) -> list[dict]:
        if stock_summary_df.empty or "Son Pozisyon Değeri (TL)" not in stock_summary_df.columns:
            return []
        df = stock_summary_df[["Hisse", "Son Pozisyon Değeri (TL)"]].copy()
        df["Son Pozisyon Değeri (TL)"] = pd.to_numeric(df["Son Pozisyon Değeri (TL)"], errors="coerce")
        df = df.dropna(subset=["Son Pozisyon Değeri (TL)"])
        total_value = df["Son Pozisyon Değeri (TL)"].sum()
        if total_value <= 0:
            return []
        df = df.sort_values("Son Pozisyon Değeri (TL)", ascending=False).reset_index(drop=True)
        top_rows = [
            {
                "ticker": row["Hisse"],
                "value": float(row["Son Pozisyon Değeri (TL)"]),
                "weight": float(row["Son Pozisyon Değeri (TL)"] / total_value),
            }
            for _, row in df.head(3).iterrows()
        ]
        remainder = float(df.iloc[3:]["Son Pozisyon Değeri (TL)"].sum())
        if remainder > 0:
            top_rows.append({"ticker": "Diğer", "value": remainder, "weight": remainder / total_value})
        return top_rows

    def _add_charts_sheet(
        self,
        writer: pd.ExcelWriter,
        summary_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
    ) -> None:
        charts_ws = writer.sheets.get(SheetName.CHARTS)
        chart_ws = writer.sheets.get(SheetName.CHART_DATA)
        stock_ws = writer.sheets.get(SheetName.STOCK_SUMMARY)
        if charts_ws is None:
            return

        charts_ws._charts = []
        period_label = self._dashboard_stats(summary_df, stock_summary_df)["period"]
        self._style_charts_sheet(charts_ws, period_label)

        if chart_ws is not None and not summary_df.empty:
            max_summary_row = len(summary_df) + 1
            categories = Reference(chart_ws, min_col=1, min_row=2, max_row=max_summary_row)
            tick_skip = max(1, len(summary_df) // 8)

            cost_basis_chart = self._cost_vs_value_chart(
                chart_ws=chart_ws,
                categories=categories,
                max_row=max_summary_row,
                tick_skip=tick_skip,
            )
            if cost_basis_chart is not None:
                charts_ws.add_chart(cost_basis_chart, "B4")

            total_return_chart = self._line_chart(
                title="Toplam Getiri Trendi (%)",
                y_axis_title="Getiri",
                data=Reference(chart_ws, min_col=5, max_col=5, min_row=1, max_row=max_summary_row),
                categories=categories,
                color=theme.GOLD_ACCENT,
                y_axis_format="0.00%",
                tick_skip=tick_skip,
                smooth=True,
            )
            charts_ws.add_chart(total_return_chart, "B24")

            drawdown_chart = self._drawdown_chart(
                chart_ws=chart_ws,
                categories=categories,
                max_row=max_summary_row,
                tick_skip=tick_skip,
            )
            charts_ws.add_chart(drawdown_chart, "N24")

        if stock_ws is not None and not stock_summary_df.empty:
            max_stock_row = len(stock_summary_df) + 1
            allocation_chart = self._allocation_doughnut(stock_ws, max_stock_row)
            charts_ws.add_chart(allocation_chart, "N4")

        self._write_charts_footer(charts_ws)

    # ────── Ortak stil ──────────────────────────────────────────────────────
    def _apply_brokerage_style(self, chart, *, transparent_plot: bool = False) -> None:
        """Tüm grafikler için kurumsal görünüm: ince Y gridline, sade legend.

        chartSpace/plotArea/axis için Excel default'ları korunur (XML uyumluluğu
        açısından en güvenli yol). Sadece Y-gridline temalı ve legend altta.
        """
        chart.height = 10
        chart.width = 18

        if getattr(chart, "x_axis", None) is not None:
            chart.x_axis.majorGridlines = None

        if getattr(chart, "y_axis", None) is not None:
            from openpyxl.chart.axis import ChartLines
            chart.y_axis.majorGridlines = ChartLines(
                spPr=GraphicalProperties(
                    ln=LineProperties(solidFill=theme.GRID_LIGHT, w=6350),
                )
            )

        if chart.legend is not None:
            chart.legend.position = "b"
            chart.legend.overlay = False

    # ────── Grafik builder'ları ────────────────────────────────────────────
    def _cost_vs_value_chart(self, chart_ws, categories, max_row, tick_skip):
        chart = LineChart()
        chart.title = "Kümülatif Portföy Değeri ve Maliyet"
        chart.y_axis.title = "TL"
        chart.x_axis.title = "Tarih"
        chart.y_axis.numFmt = '#,##0 "TL"'
        chart.x_axis.numFmt = "dd.mm.yy"
        chart.x_axis.tickLblSkip = tick_skip
        chart.x_axis.tickMarkSkip = tick_skip

        chart.add_data(
            Reference(chart_ws, min_col=2, max_col=2, min_row=1, max_row=max_row),
            titles_from_data=True,
        )
        chart.add_data(
            Reference(chart_ws, min_col=7, max_col=7, min_row=1, max_row=max_row),
            titles_from_data=True,
        )
        chart.set_categories(categories)

        if len(chart.series) >= 2:
            value_series = chart.series[0]
            cost_series = chart.series[1]
            value_series.graphicalProperties.line.solidFill = theme.NAVY_DEEP
            value_series.graphicalProperties.line.width = 28000
            value_series.smooth = False

            cost_series.graphicalProperties.line.solidFill = theme.SLATE
            cost_series.graphicalProperties.line.width = 22000
            cost_series.graphicalProperties.line.dashStyle = "dash"
            cost_series.smooth = False

        self._apply_brokerage_style(chart)
        return chart

    def _drawdown_chart(self, chart_ws, categories, max_row, tick_skip):
        chart = AreaChart()
        chart.title = "Drawdown (Tepe Dipten)"
        chart.y_axis.title = "Drawdown"
        chart.x_axis.title = "Tarih"
        chart.y_axis.numFmt = "0.00%;-0.00%"
        chart.x_axis.numFmt = "dd.mm.yy"
        chart.x_axis.tickLblSkip = tick_skip
        chart.x_axis.tickMarkSkip = tick_skip
        chart.legend = None

        chart.add_data(
            Reference(chart_ws, min_col=6, max_col=6, min_row=1, max_row=max_row),
            titles_from_data=True,
        )
        chart.set_categories(categories)

        if chart.series:
            series = chart.series[0]
            series.graphicalProperties = GraphicalProperties(solidFill="FFCDD2")
            series.graphicalProperties.line.solidFill = theme.NEGATIVE

        self._apply_brokerage_style(chart, transparent_plot=True)
        return chart

    def _daily_return_bar_chart(self, chart_ws, categories, max_row, tick_skip):
        chart = BarChart()
        chart.type = "col"
        chart.title = "Günlük Getiri Dağılımı"
        chart.y_axis.title = "Günlük Getiri"
        chart.x_axis.title = "Tarih"
        chart.legend = None
        chart.gapWidth = 80
        chart.overlap = 100
        chart.y_axis.numFmt = "0.00%"
        chart.x_axis.numFmt = "dd.mm.yy"
        chart.x_axis.tickLblSkip = tick_skip
        chart.x_axis.tickMarkSkip = tick_skip

        chart.add_data(
            Reference(chart_ws, min_col=3, max_col=4, min_row=1, max_row=max_row),
            titles_from_data=True,
        )
        chart.set_categories(categories)

        if len(chart.series) >= 2:
            chart.series[0].graphicalProperties = GraphicalProperties(solidFill=theme.POSITIVE)
            chart.series[1].graphicalProperties = GraphicalProperties(solidFill=theme.NEGATIVE)

        self._apply_brokerage_style(chart)
        return chart

    def _allocation_doughnut(self, stock_ws, max_stock_row):
        chart = DoughnutChart()
        chart.title = "Hisse Dağılımı"
        chart.height = 12
        chart.width = 14
        chart.holeSize = 55
        chart.firstSliceAng = 270

        chart.add_data(
            Reference(stock_ws, min_col=5, max_col=5, min_row=1, max_row=max_stock_row),
            titles_from_data=True,
        )
        chart.set_categories(
            Reference(stock_ws, min_col=1, min_row=2, max_row=max_stock_row)
        )

        if chart.series:
            series = chart.series[0]
            n_slices = max_stock_row - 1
            data_points = []
            for idx in range(n_slices):
                color = theme.DOUGHNUT_PALETTE[idx % len(theme.DOUGHNUT_PALETTE)]
                dp = DataPoint(idx=idx)
                dp.graphicalProperties = GraphicalProperties(solidFill=color)
                data_points.append(dp)
            series.data_points = data_points

        chart.dataLabels = DataLabelList(
            showPercent=True,
            showCatName=True,
            showVal=False,
            showSerName=False,
            showLegendKey=False,
        )

        if chart.legend is not None:
            chart.legend.position = "r"
            chart.legend.overlay = False
        return chart

    def _weight_horizontal_bar(self, stock_ws, stock_summary_df):
        if stock_summary_df.empty or "Son Pozisyon Değeri (TL)" not in stock_summary_df.columns:
            return None

        df = stock_summary_df.copy()
        df["__val"] = pd.to_numeric(df["Son Pozisyon Değeri (TL)"], errors="coerce")
        df = df.dropna(subset=["__val"])
        if df.empty:
            return None

        df = df.sort_values("__val", ascending=False).reset_index(drop=True).head(10)
        ordered_tickers = df["Hisse"].tolist()

        original_index_by_ticker = {
            ticker: idx for idx, ticker in enumerate(stock_summary_df["Hisse"].tolist())
        }

        chart = BarChart()
        chart.type = "bar"
        chart.title = "Hisse Ağırlığı (İlk 10)"
        chart.x_axis.title = "Pozisyon Değeri (TL)"
        chart.legend = None
        chart.gapWidth = 80
        chart.x_axis.numFmt = '#,##0 "TL"'

        max_row = len(stock_summary_df) + 1
        chart.add_data(
            Reference(stock_ws, min_col=5, max_col=5, min_row=1, max_row=max_row),
            titles_from_data=True,
        )
        chart.set_categories(
            Reference(stock_ws, min_col=1, min_row=2, max_row=max_row)
        )

        if chart.series:
            series = chart.series[0]
            series.graphicalProperties = GraphicalProperties(solidFill=theme.NAVY_DEEP)
            series.dLbls = DataLabelList(
                showVal=True,
                showCatName=False,
                showSerName=False,
                showLegendKey=False,
                dLblPos="outEnd",
            )

        self._apply_brokerage_style(chart)
        _ = ordered_tickers, original_index_by_ticker
        return chart

    def _style_charts_sheet(self, worksheet, period_label: str | None = None) -> None:
        worksheet.sheet_view.showGridLines = False
        for column_idx in range(1, 26):
            worksheet.column_dimensions[get_column_letter(column_idx)].width = 12
        for row_idx in range(1, 90):
            worksheet.row_dimensions[row_idx].height = 20

        worksheet.merge_cells("A1:Z1")
        banner = worksheet["A1"]
        banner.value = "Portföy Performans Raporu — Grafikler"
        banner.font = Font(bold=True, color=theme.WHITE, size=16)
        banner.fill = PatternFill(start_color=theme.NAVY_PRIMARY, end_color=theme.NAVY_PRIMARY, fill_type="solid")
        banner.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.row_dimensions[1].height = 32

        worksheet.merge_cells("A2:Z2")
        sub = worksheet["A2"]
        sub.value = f"Rapor dönemi: {period_label}" if period_label and period_label != "Veri yok" else "Rapor dönemi: —"
        sub.font = Font(italic=True, color=theme.SLATE, size=10)
        sub.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.row_dimensions[2].height = 22

        subtitles = {
            "B3":  "Portföy değeri ile alım maliyeti karşılaştırması",
            "B23": "Kümülatif getiri yüzdesi (%)",
            "N3":  "Hisse senedi ağırlık dağılımı",
            "N23": "Tepe değerden maksimum düşüş — risk ölçütü",
        }
        for cell_ref, text in subtitles.items():
            cell = worksheet[cell_ref]
            cell.value = text
            cell.font = Font(italic=True, color=theme.TEXT_MUTED, size=9)
            cell.alignment = Alignment(vertical="center")
        worksheet.row_dimensions[3].height = 18
        worksheet.row_dimensions[23].height = 18

    def _write_charts_footer(self, worksheet) -> None:
        footer_row = 85
        worksheet.merge_cells(start_row=footer_row, start_column=1, end_row=footer_row, end_column=26)
        cell = worksheet.cell(row=footer_row, column=1)
        cell.value = (
            "Veriler portföy işlem geçmişinden hesaplanmıştır. BIST kapalı günleri "
            "ve fiyat verisi olmayan günler performans serisine dahil edilmez."
        )
        cell.font = Font(italic=True, color=theme.TEXT_MUTED, size=9)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        worksheet.row_dimensions[footer_row].height = 28

    # ────── 1. Tab renklendirme + 5. Yazdırma ayarları ──────────────────────
    _TAB_COLORS = {
        SheetName.DASHBOARD:     "FF0D2B6E",
        SheetName.CHARTS:        "FFF9A825",
        SheetName.SUMMARY:       "FF00897B",
        SheetName.DAILY_DETAIL:  "FF455A64",
        SheetName.STOCK_SUMMARY: "FF1565C0",
        SheetName.CHART_DATA:    "FF90A4AE",
    }

    def _post_process_sheets(self, workbook) -> None:
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

    # ────── 2. Dashboard KPI kartları ────────────────────────────────────────
    def _style_dashboard_kpi(self, worksheet, dashboard_df: "pd.DataFrame") -> None:
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

    # ────── 4. Veri sayfaları üst banner ─────────────────────────────────────
    def _add_banner_to_data_sheet(self, worksheet, title: str, ncols: int) -> None:
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

    def _style_dashboard_sheet(self, worksheet) -> None:
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

    def _write_dashboard_summaries(
        self,
        worksheet,
        summary_df: pd.DataFrame,
        stock_summary_df: pd.DataFrame,
    ) -> None:
        stats = self._dashboard_stats(summary_df, stock_summary_df)
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
            f"Grafiklerde tarih ekseni {stats['period']} dönemini kapsar; yoğun günler metin özetinde net tarihlerle açıklanır.",
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
            worksheet.cell(row=row_offset, column=2, value=self._fmt_tl(holding["value"]))
            worksheet.cell(row=row_offset, column=3, value=self._fmt_pct_value(holding["weight"]))
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

    def _line_chart(
        self,
        title: str,
        y_axis_title: str,
        data: Reference,
        categories: Reference,
        color: str,
        y_axis_format: str,
        tick_skip: int,
        smooth: bool = False,
        highlight_last_point: bool = False,
        last_label_format: str | None = None,
        series_length: int = 0,
    ) -> LineChart:
        chart = LineChart()
        chart.title = title
        chart.y_axis.title = y_axis_title
        chart.x_axis.title = "Tarih"
        chart.legend = None
        chart.y_axis.numFmt = y_axis_format
        chart.x_axis.numFmt = "dd.mm.yy"
        chart.x_axis.tickLblSkip = tick_skip
        chart.x_axis.tickMarkSkip = tick_skip
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        if chart.series:
            series = chart.series[0]
            series.graphicalProperties.line.solidFill = color
            series.graphicalProperties.line.width = 28000
            series.smooth = smooth
        _ = highlight_last_point, last_label_format, series_length
        self._apply_brokerage_style(chart)
        return chart

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
                chart_data_df = self._build_chart_data_df(summary_df)
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
                self._add_charts_sheet(writer, summary_df, stock_summary_df)
                self._style_dashboard_kpi(writer.sheets[SheetName.DASHBOARD], dashboard_df)
                self._add_banner_to_data_sheet(writer.sheets[SheetName.SUMMARY],       "Portföy Özeti",     len(summary_df.columns))
                self._add_banner_to_data_sheet(writer.sheets[SheetName.DAILY_DETAIL],  "Günlük Detaylar",   len(detail_df.columns))
                self._add_banner_to_data_sheet(writer.sheets[SheetName.STOCK_SUMMARY], "Hisse Özeti",       len(stock_summary_df.columns))
                self._post_process_sheets(writer.book)
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
            combined_summary = self.normalize_date_column(combined_summary)
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
            combined_detail = self.normalize_date_column(combined_detail)
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
                chart_data_df = self._build_chart_data_df(combined_summary)
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
                self._add_charts_sheet(writer, combined_summary, combined_stock_sum)
                self._style_dashboard_kpi(writer.sheets[SheetName.DASHBOARD], dashboard_df)
                self._add_banner_to_data_sheet(writer.sheets[SheetName.SUMMARY],       "Portföy Özeti",     len(combined_summary.columns))
                self._add_banner_to_data_sheet(writer.sheets[SheetName.DAILY_DETAIL],  "Günlük Detaylar",   len(combined_detail.columns))
                self._add_banner_to_data_sheet(writer.sheets[SheetName.STOCK_SUMMARY], "Hisse Özeti",       len(combined_stock_sum.columns))
                self._post_process_sheets(writer.book)
        except PermissionError:
            raise PermissionError(
                f"Dosyaya yazılamadı: {file_path}\n"
                "Dosya açık olabilir. Lütfen kapatıp tekrar deneyin."
            )
