# src/ui/pages/stock_detail/stock_chart_widget.py

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

import pyqtgraph as pg
import yfinance as yf
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QSizePolicy, QVBoxLayout

from src.ui.formatters import display_ticker

logger = logging.getLogger(__name__)

BG_BASE = "#0f172a"
BORDER = "#334155"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
LINE_BLUE = "#3b82f6"
LINE_CURRENT = "#10b981"
LINE_AVG_COST = "#f59e0b"


class DateAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):  # noqa: N802 - pyqtgraph API
        labels = []
        for value in values:
            try:
                labels.append(datetime.fromtimestamp(value).strftime("%d %b"))
            except (OSError, OverflowError, ValueError):
                labels.append("")
        return labels


class StockChartWidget(QFrame):
    """Hisse fiyat grafiğini çizen bağımsız bileşen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "chartWidget")
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._init_ui()

    def _init_ui(self):
        pg.setConfigOptions(antialias=True, background=BG_BASE, foreground=TEXT_SECONDARY)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget(axisItems={"bottom": DateAxisItem(orientation="bottom")})
        self.plot_widget.setBackground(BG_BASE)
        self.plot_widget.setMinimumHeight(320)
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.plot_widget)
        self._reference_legend = None

        self._configure_plot_item()
        self.draw_empty_chart("Grafik verisi bekleniyor")

    def _configure_plot_item(self) -> None:
        plot_item = self.plot_widget.getPlotItem()
        plot_item.showGrid(x=True, y=True, alpha=0.14)
        plot_item.setMenuEnabled(False)
        plot_item.hideButtons()
        plot_item.setLabel("bottom", "Tarih", color=TEXT_SECONDARY)
        plot_item.setLabel("left", "", color=TEXT_SECONDARY)
        plot_item.setContentsMargins(8, 8, 12, 8)
        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(BORDER))
            axis.setTextPen(pg.mkPen(TEXT_SECONDARY))
            axis.setStyle(tickTextOffset=8)
            if hasattr(axis, "enableAutoSIPrefix"):
                axis.enableAutoSIPrefix(False)

    def draw_empty_chart(self, message: str) -> None:
        self.plot_widget.clear()
        self._clear_reference_legend()
        self._configure_plot_item()
        self.plot_widget.getPlotItem().setTitle(message, color=TEXT_SECONDARY, size="13pt")
        self.plot_widget.enableAutoRange()

    def draw_chart(self, current_ticker: str, current_stock_id, current_price, portfolio_service):
        if not current_ticker:
            self.draw_empty_chart("Grafik verisi bekleniyor")
            return

        self.plot_widget.clear()
        self._clear_reference_legend()
        self._configure_plot_item()
        plot_item = self.plot_widget.getPlotItem()
        plot_item.setTitle(
            f"{display_ticker(current_ticker)} - Fiyat Geçmişi",
            color=TEXT_PRIMARY,
            size="15pt",
        )

        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=180)

            yf_ticker = current_ticker if "." in current_ticker else f"{current_ticker}.IS"
            data = yf.download(
                yf_ticker,
                start=start_date,
                end=end_date + timedelta(days=1),
                progress=False,
                auto_adjust=False,
            )

            if data is None or data.empty:
                self.draw_empty_chart("Veri bulunamadı")
                return

            close_col = "Close" if "Close" in data.columns else data.columns[0]
            close_data = data[close_col]
            if hasattr(close_data, "values") and len(close_data.shape) > 1:
                close_data = close_data.iloc[:, 0]

            points = self._series_to_points(close_data)
            if not points:
                self.draw_empty_chart("Veri bulunamadı")
                return

            x_values = [point[0] for point in points]
            y_values = [point[1] for point in points]

            curve = self.plot_widget.plot(
                x_values,
                y_values,
                pen=pg.mkPen(LINE_BLUE, width=3),
                symbol=None,
                name="Fiyat",
            )
            baseline = min(y_values)
            baseline_curve = pg.PlotDataItem(x_values, [baseline] * len(x_values), pen=pg.mkPen(None))
            fill = pg.FillBetweenItem(curve, baseline_curve, brush=pg.mkBrush(59, 130, 246, 34))
            self.plot_widget.addItem(baseline_curve)
            self.plot_widget.addItem(fill)

            ymin = min(y_values)
            ymax = max(y_values)
            padding = (ymax - ymin) * 0.12 if ymax > ymin else max(ymax * 0.1, 1.0)
            self.plot_widget.setYRange(max(0, ymin - padding), ymax + padding, padding=0)

            avg_cost = self._average_cost(current_stock_id, portfolio_service)
            if avg_cost is not None:
                self._add_reference_line(avg_cost, "Ort. Maliyet", LINE_AVG_COST, Qt.DashLine)

            if current_price:
                self._add_reference_line(float(current_price), f"Güncel: {float(current_price):.2f}", LINE_CURRENT, Qt.SolidLine)

            self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)
        except Exception as exc:
            logger.error("Grafik hatası: %s", exc)
            self.draw_empty_chart("Grafik yüklenemedi")

    def _add_reference_line(self, value: float, label: str, color: str, style: Qt.PenStyle) -> None:
        pen = pg.mkPen(color, width=1.4, style=style)
        line = pg.InfiniteLine(
            pos=value,
            angle=0,
            movable=False,
            pen=pen,
        )
        self.plot_widget.addItem(line)
        self._add_reference_legend_item(label, pen)

    def _add_reference_legend_item(self, label: str, pen) -> None:
        if self._reference_legend is None:
            self._reference_legend = pg.LegendItem(
                offset=(14, 14),
                brush=pg.mkBrush(15, 23, 42, 220),
                pen=pg.mkPen(BORDER),
                labelTextColor=TEXT_PRIMARY,
            )
            self._reference_legend.setParentItem(self.plot_widget.getPlotItem().graphicsItem())
        sample = pg.PlotDataItem([], [], pen=pen)
        self._reference_legend.addItem(sample, label)

    def _clear_reference_legend(self) -> None:
        if self._reference_legend is not None:
            legend = self._reference_legend
            self._reference_legend = None
            scene = legend.scene()
            if scene is not None:
                scene.removeItem(legend)

    @staticmethod
    def _average_cost(current_stock_id, portfolio_service) -> float | None:
        if not current_stock_id or not portfolio_service:
            return None
        portfolio = portfolio_service.get_current_portfolio()
        pos = portfolio.positions.get(current_stock_id)
        if not pos or not pos.average_cost:
            return None
        return float(pos.average_cost)

    @staticmethod
    def _series_to_points(close_data) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for index_value, raw_value in close_data.dropna().items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not value:
                continue

            if hasattr(index_value, "to_pydatetime"):
                dt = index_value.to_pydatetime()
            elif isinstance(index_value, datetime):
                dt = index_value
            elif isinstance(index_value, date):
                dt = datetime.combine(index_value, time.min)
            else:
                continue
            points.append((dt.timestamp(), value))
        return points
