from __future__ import annotations

import pandas as pd
from openpyxl.chart import AreaChart, BarChart, DoughnutChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties

from src.application.services.reporting import excel_theme as theme


class ExcelChartFactory:
    def apply_brokerage_style(self, chart, *, transparent_plot: bool = False) -> None:
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

    def cost_vs_value_chart(self, chart_ws, categories, max_row, tick_skip):
        chart = LineChart()
        chart.title = "Kümülatif Portföy Değeri ve Maliyet"
        chart.y_axis.title = "TL"
        chart.x_axis.title = "Tarih"
        chart.y_axis.numFmt = '#,##0 "TL"'
        chart.x_axis.numFmt = "dd.mm.yy"
        chart.x_axis.tickLblSkip = tick_skip
        chart.x_axis.tickMarkSkip = tick_skip
        chart.add_data(Reference(chart_ws, min_col=2, max_col=2, min_row=1, max_row=max_row), titles_from_data=True)
        chart.add_data(Reference(chart_ws, min_col=7, max_col=7, min_row=1, max_row=max_row), titles_from_data=True)
        chart.set_categories(categories)
        self._style_value_and_cost_series(chart)
        self.apply_brokerage_style(chart)
        return chart

    @staticmethod
    def _style_value_and_cost_series(chart) -> None:
        if len(chart.series) < 2:
            return
        value_series = chart.series[0]
        cost_series = chart.series[1]
        value_series.graphicalProperties.line.solidFill = theme.NAVY_DEEP
        value_series.graphicalProperties.line.width = 28000
        value_series.smooth = False
        cost_series.graphicalProperties.line.solidFill = theme.SLATE
        cost_series.graphicalProperties.line.width = 22000
        cost_series.graphicalProperties.line.dashStyle = "dash"
        cost_series.smooth = False

    def drawdown_chart(self, chart_ws, categories, max_row, tick_skip):
        chart = AreaChart()
        chart.title = "Drawdown (Tepe Dipten)"
        chart.y_axis.title = "Drawdown"
        chart.x_axis.title = "Tarih"
        chart.y_axis.numFmt = "0.00%;-0.00%"
        chart.x_axis.numFmt = "dd.mm.yy"
        chart.x_axis.tickLblSkip = tick_skip
        chart.x_axis.tickMarkSkip = tick_skip
        chart.legend = None
        chart.add_data(Reference(chart_ws, min_col=6, max_col=6, min_row=1, max_row=max_row), titles_from_data=True)
        chart.set_categories(categories)
        if chart.series:
            series = chart.series[0]
            series.graphicalProperties = GraphicalProperties(solidFill="FFCDD2")
            series.graphicalProperties.line.solidFill = theme.NEGATIVE
        self.apply_brokerage_style(chart, transparent_plot=True)
        return chart

    def allocation_doughnut(self, stock_ws, max_stock_row):
        chart = DoughnutChart()
        chart.title = "Hisse Dağılımı"
        chart.height = 12
        chart.width = 14
        chart.holeSize = 55
        chart.firstSliceAng = 270
        chart.add_data(Reference(stock_ws, min_col=5, max_col=5, min_row=1, max_row=max_stock_row), titles_from_data=True)
        chart.set_categories(Reference(stock_ws, min_col=1, min_row=2, max_row=max_stock_row))
        self._style_doughnut_points(chart, max_stock_row)
        chart.dataLabels = DataLabelList(showPercent=True, showCatName=True, showVal=False, showSerName=False, showLegendKey=False)
        if chart.legend is not None:
            chart.legend.position = "r"
            chart.legend.overlay = False
        return chart

    @staticmethod
    def _style_doughnut_points(chart, max_stock_row: int) -> None:
        if not chart.series:
            return
        data_points = []
        for idx in range(max_stock_row - 1):
            dp = DataPoint(idx=idx)
            dp.graphicalProperties = GraphicalProperties(solidFill=theme.DOUGHNUT_PALETTE[idx % len(theme.DOUGHNUT_PALETTE)])
            data_points.append(dp)
        chart.series[0].data_points = data_points

    def line_chart(
        self,
        title: str,
        y_axis_title: str,
        data: Reference,
        categories: Reference,
        color: str,
        y_axis_format: str,
        tick_skip: int,
        smooth: bool = False,
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
        self.apply_brokerage_style(chart)
        return chart

    def daily_return_bar_chart(self, chart_ws, categories, max_row, tick_skip):
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
        chart.add_data(Reference(chart_ws, min_col=3, max_col=4, min_row=1, max_row=max_row), titles_from_data=True)
        chart.set_categories(categories)
        if len(chart.series) >= 2:
            chart.series[0].graphicalProperties = GraphicalProperties(solidFill=theme.POSITIVE)
            chart.series[1].graphicalProperties = GraphicalProperties(solidFill=theme.NEGATIVE)
        self.apply_brokerage_style(chart)
        return chart

    def weight_horizontal_bar(self, stock_ws, stock_summary_df: pd.DataFrame):
        if stock_summary_df.empty or "Son Pozisyon Değeri (TL)" not in stock_summary_df.columns:
            return None
        df = stock_summary_df.copy()
        df["__val"] = pd.to_numeric(df["Son Pozisyon Değeri (TL)"], errors="coerce")
        df = df.dropna(subset=["__val"])
        if df.empty:
            return None

        chart = BarChart()
        chart.type = "bar"
        chart.title = "Hisse Ağırlığı (İlk 10)"
        chart.x_axis.title = "Pozisyon Değeri (TL)"
        chart.legend = None
        chart.gapWidth = 80
        chart.x_axis.numFmt = '#,##0 "TL"'
        max_row = len(stock_summary_df) + 1
        chart.add_data(Reference(stock_ws, min_col=5, max_col=5, min_row=1, max_row=max_row), titles_from_data=True)
        chart.set_categories(Reference(stock_ws, min_col=1, min_row=2, max_row=max_row))
        if chart.series:
            series = chart.series[0]
            series.graphicalProperties = GraphicalProperties(solidFill=theme.NAVY_DEEP)
            series.dLbls = DataLabelList(showVal=True, showCatName=False, showSerName=False, showLegendKey=False, dLblPos="outEnd")
        self.apply_brokerage_style(chart)
        return chart
