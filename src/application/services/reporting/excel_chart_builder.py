# src/application/services/reporting/excel_chart_builder.py

import pandas as pd
from openpyxl.chart import AreaChart, BarChart, DoughnutChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.application.services.reporting import excel_theme as theme
from src.application.services.reporting.daily_history_models import SheetName
from src.application.services.reporting.excel_data_preparer import ExcelDataPreparer


class ExcelChartBuilder:
    def __init__(self, data_preparer: ExcelDataPreparer) -> None:
        self.data_preparer = data_preparer

    def add_charts_sheet(
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
        period_label = self.data_preparer.dashboard_stats(summary_df, stock_summary_df)["period"]
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

    def _apply_brokerage_style(self, chart, *, transparent_plot: bool = False) -> None:
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
