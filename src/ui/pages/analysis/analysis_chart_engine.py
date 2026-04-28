# src/ui/pages/analysis/analysis_chart_engine.py

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple

import pyqtgraph as pg
import pyqtgraph.exporters
from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


BG_BASE = "#0f172a"
BG_SURFACE = "#1e293b"
BORDER = "#334155"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
ACCENT = "#38bdf8"


@dataclass(frozen=True)
class PreparedSeries:
    label: str
    x_values: List[float]
    y_values: List[float]
    color: str
    is_primary: bool
    trimmed_points: int


class DateAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):  # noqa: N802 - pyqtgraph API
        labels = []
        for value in values:
            try:
                labels.append(datetime.fromtimestamp(value).strftime("%d/%m"))
            except (OSError, OverflowError, ValueError):
                labels.append("")
        return labels


class PieChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._title = ""
        self._breakdown: List[Tuple[str, float]] = []
        self._message = "Grafik verisi bekleniyor"
        self._colors = [
            "#38bdf8",
            "#f97316",
            "#22c55e",
            "#ef4444",
            "#a78bfa",
            "#f472b6",
            "#facc15",
            "#14b8a6",
            "#fb7185",
            "#60a5fa",
        ]
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_empty(self, message: str) -> None:
        self._title = ""
        self._breakdown = []
        self._message = message
        self.update()

    def set_data(self, title: str, breakdown: List[Tuple[str, float]]) -> None:
        self._title = title
        self._breakdown = list(breakdown)
        self._message = ""
        self.update()

    def colors(self) -> List[str]:
        return self._colors

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(BG_BASE))

        painter.setPen(QColor(TEXT_PRIMARY))
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(QRectF(0, 12, self.width(), 28), Qt.AlignCenter, self._title or "Dağılım")

        if not self._breakdown:
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(self.rect(), Qt.AlignCenter, self._message)
            return

        total = sum(value for _, value in self._breakdown)
        if total <= 0:
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(self.rect(), Qt.AlignCenter, "Dağılım için pozitif değer yok")
            return

        side = max(140, min(self.width() - 30, self.height() - 95))
        pie_rect = QRectF((self.width() - side) / 2, 54, side, side)
        start_angle = 90 * 16
        for idx, (_, value) in enumerate(self._breakdown):
            span = int(-(value / total) * 360 * 16)
            painter.setBrush(QColor(self._colors[idx % len(self._colors)]))
            painter.setPen(QPen(QColor(BG_BASE), 2))
            painter.drawPie(pie_rect, start_angle, span)

            mid_angle = (start_angle + span / 2) / 16
            label_radius = side * 0.33
            center = pie_rect.center()
            label_x = center.x() + math.cos(math.radians(mid_angle)) * label_radius
            label_y = center.y() - math.sin(math.radians(mid_angle)) * label_radius
            pct = (value / total) * 100
            self._draw_slice_label(
                painter,
                label=f"{self._break_label(self._breakdown[idx][0])}\n%{pct:.1f}",
                center_x=label_x,
                center_y=label_y,
                compact=pct < 8,
            )
            start_angle += span

    def _draw_slice_label(self, painter: QPainter, label: str, center_x: float, center_y: float, compact: bool) -> None:
        font = QFont()
        font.setPointSize(7 if compact else 8)
        font.setBold(True)
        painter.setFont(font)
        label_rect = QRectF(center_x - 38, center_y - 16, 76, 32)
        painter.setBrush(QColor(15, 23, 42, 175))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(label_rect, 5, 5)
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(label_rect, Qt.AlignCenter, label)

    @staticmethod
    def _break_label(label: str) -> str:
        if len(label) <= 8:
            return label
        if "." in label:
            head, tail = label.rsplit(".", 1)
            return f"{head[:5]}.\n{tail}"
        return label[:8]


class AnalysisChartEngine(QWidget):
    """
    Analiz sayfasındaki çizim motoru.
    Çizgi grafikleri pyqtgraph ile, dağılım grafikleri hafif Qt painter widget'ı ile çizer.
    """

    hover_changed = pyqtSignal(str)

    def __init__(self, parent=None, show_toolbar: bool = True):
        super().__init__(parent)
        self._show_toolbar = show_toolbar
        self._prepared_series: List[PreparedSeries] = []
        self._plot_items: list = []
        self._init_ui()

    def _init_ui(self):
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pg.setConfigOptions(antialias=True, background=BG_BASE, foreground=TEXT_SECONDARY)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.chart_row = QHBoxLayout()
        self.chart_row.setContentsMargins(0, 0, 0, 0)
        self.chart_row.setSpacing(12)

        self.plot_widget = pg.PlotWidget(axisItems={"bottom": DateAxisItem(orientation="bottom")})
        self.plot_widget.setBackground(BG_BASE)
        self.plot_widget.setMinimumHeight(360)
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._configure_plot_item()
        self.chart_row.addWidget(self.plot_widget, 1)

        self.pie_widget = PieChartWidget()
        self.pie_widget.hide()
        self.chart_row.addWidget(self.pie_widget, 1)

        self.legend_panel = QFrame()
        self.legend_panel.setObjectName("analysisSeriesLegend")
        self.legend_panel.setMinimumWidth(170)
        self.legend_panel.setMaximumWidth(230)
        self.legend_layout = QVBoxLayout(self.legend_panel)
        self.legend_layout.setContentsMargins(10, 10, 10, 10)
        self.legend_layout.setSpacing(7)
        self.chart_row.addWidget(self.legend_panel, 0)

        layout.addLayout(self.chart_row, 1)

        self.lbl_summary = QLabel("Grafik verisi bekleniyor")
        self.lbl_summary.setProperty("cssClass", "chartSummaryText")
        self.lbl_summary.setWordWrap(True)
        layout.addWidget(self.lbl_summary)

        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(TEXT_MUTED, width=1, style=Qt.DashLine))
        self.v_line.hide()
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.hover_label = pg.TextItem("", color=TEXT_PRIMARY, fill=pg.mkBrush(15, 23, 42, 230), border=pg.mkPen(BORDER))
        self.hover_label.hide()
        self.plot_widget.addItem(self.hover_label, ignoreBounds=True)
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=30, slot=self._on_mouse_moved)

        self.draw_empty_chart("Grafik verisi bekleniyor")

    def _configure_plot_item(self) -> None:
        plot_item = self.plot_widget.getPlotItem()
        plot_item.showGrid(x=True, y=True, alpha=0.16)
        plot_item.setMenuEnabled(False)
        plot_item.hideButtons()
        plot_item.setLabel("bottom", "Tarih", color=TEXT_SECONDARY)
        plot_item.setLabel("left", "", color=TEXT_SECONDARY)
        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(BORDER))
            axis.setTextPen(pg.mkPen(TEXT_SECONDARY))
            axis.setStyle(tickTextOffset=8)
            if axis_name == "bottom" and hasattr(axis, "enableAutoSIPrefix"):
                axis.enableAutoSIPrefix(False)

    def draw_empty_chart(self, message: str):
        self._show_plot()
        self.plot_widget.clear()
        self._plot_items = []
        self._prepared_series = []
        self._configure_plot_item()
        self.plot_widget.getPlotItem().setTitle(message, color=TEXT_SECONDARY, size="13pt")
        self._clear_legend()
        self._add_legend_label(message, TEXT_SECONDARY)
        self.legend_panel.show()
        self.lbl_summary.setText(message)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(TEXT_MUTED, width=1, style=Qt.DashLine))
        self.v_line.hide()
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.hover_label = pg.TextItem("", color=TEXT_PRIMARY, fill=pg.mkBrush(15, 23, 42, 230), border=pg.mkPen(BORDER))
        self.hover_label.hide()
        self.plot_widget.addItem(self.hover_label, ignoreBounds=True)

    def draw_line_series(
        self,
        title: str,
        y_label: str,
        series_map: Dict[str, Dict[date, Decimal | float]],
        normalize: bool = False,
        baseline: float | None = None,
    ):
        self._show_plot()
        self.plot_widget.clear()
        self._configure_plot_item()
        self.plot_widget.getPlotItem().setTitle(title, color=TEXT_PRIMARY, size="15pt")
        self.plot_widget.getPlotItem().setLabel("left", y_label, color=TEXT_SECONDARY)
        self._clear_legend()
        self.legend_panel.show()

        self._prepared_series = self._prepare_line_series(series_map, normalize=normalize)
        if not self._prepared_series:
            self.draw_empty_chart("Veri bulunamadı")
            return

        if baseline is not None:
            baseline_item = pg.InfiniteLine(
                pos=baseline,
                angle=0,
                movable=False,
                pen=pg.mkPen("#64748b", width=1.4, style=Qt.DashLine),
            )
            self.plot_widget.addItem(baseline_item)

        self._plot_items = []
        for series in self._prepared_series:
            line_color = QColor(series.color)
            if not series.is_primary:
                line_color.setAlpha(190)
            pen = pg.mkPen(line_color, width=3.2 if series.is_primary else 1.8)
            item = self.plot_widget.plot(series.x_values, series.y_values, pen=pen, symbol=None, name=series.label)
            item.setZValue(10 if series.is_primary else 3)
            self._plot_items.append(item)
            self._add_legend_row(series)

        self.plot_widget.enableAutoRange()
        trimmed = sum(series.trimmed_points for series in self._prepared_series)
        extra = f" - {trimmed} başlangıç noktası kırpıldı" if trimmed else ""
        self.lbl_summary.setText(f"{len(self._prepared_series)} seri gösteriliyor{extra}")

        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(TEXT_MUTED, width=1, style=Qt.DashLine))
        self.v_line.hide()
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.hover_label = pg.TextItem("", color=TEXT_PRIMARY, fill=pg.mkBrush(15, 23, 42, 235), border=pg.mkPen(BORDER))
        self.hover_label.hide()
        self.plot_widget.addItem(self.hover_label, ignoreBounds=True)

    def draw_portfolio_pie(self, title: str, breakdown: List[Tuple[str, float]]):
        self._show_pie()
        clean_breakdown = [(label, float(value)) for label, value in breakdown if value > 0]
        self._clear_legend()
        self.legend_panel.hide()
        if not clean_breakdown:
            self.pie_widget.set_empty("Portföyde pozisyon yok veya değer hesaplanamadı")
            self.lbl_summary.setText("Portföyde pozisyon yok veya değer hesaplanamadı")
            return

        self.pie_widget.set_data(title, clean_breakdown)
        total = sum(value for _, value in clean_breakdown)
        self.lbl_summary.setText(f"Toplam {len(clean_breakdown)} pozisyon, ₺{total:,.2f}")

    def save_chart(self, file_path: str):
        suffix = Path(file_path).suffix.lower()
        target_widget: QWidget = self.pie_widget if self.pie_widget.isVisible() else self.plot_widget

        if suffix == ".svg" and target_widget is self.plot_widget:
            exporter = pg.exporters.SVGExporter(self.plot_widget.getPlotItem())
            exporter.export(file_path)
            return
        if suffix in {".png", ".jpg", ".jpeg"} and target_widget is self.plot_widget:
            exporter = pg.exporters.ImageExporter(self.plot_widget.getPlotItem())
            exporter.parameters()["width"] = max(1200, self.plot_widget.width())
            exporter.export(file_path)
            return
        if suffix == ".pdf":
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            painter = QPainter(printer)
            target_widget.render(painter)
            painter.end()
            return

        target_widget.grab().save(file_path)

    def _show_plot(self) -> None:
        self.pie_widget.hide()
        self.plot_widget.show()
        self.legend_panel.show()

    def _show_pie(self) -> None:
        self.plot_widget.hide()
        self.pie_widget.show()
        self.legend_panel.hide()

    def _prepare_line_series(
        self,
        series_map: Dict[str, Dict[date, Decimal | float]],
        normalize: bool,
    ) -> List[PreparedSeries]:
        palette = [
            ACCENT,
            "#f97316",
            "#22c55e",
            "#ef4444",
            "#a78bfa",
            "#f472b6",
            "#facc15",
            "#14b8a6",
            "#fb7185",
            "#60a5fa",
        ]
        prepared: List[PreparedSeries] = []
        for idx, (label, points) in enumerate(series_map.items()):
            sorted_points = sorted(points.items(), key=lambda item: item[0])
            raw = [(point_date, float(value)) for point_date, value in sorted_points if value is not None]
            if normalize:
                first_positive_index = next((i for i, (_, value) in enumerate(raw) if value > 0), None)
                if first_positive_index is None:
                    continue
                trimmed_points = first_positive_index
                raw = raw[first_positive_index:]
                base = raw[0][1]
                if base <= 0:
                    continue
                values = [(point_date, (value / base) * 100) for point_date, value in raw if value > 0]
            else:
                trimmed_points = 0
                values = [(point_date, value) for point_date, value in raw if math.isfinite(value)]
            if not values:
                continue

            x_values = [self._date_to_x(point_date) for point_date, _ in values]
            y_values = [value for _, value in values]
            prepared.append(
                PreparedSeries(
                    label=label,
                    x_values=x_values,
                    y_values=y_values,
                    color=palette[idx % len(palette)],
                    is_primary=label == "Ana Portföy" or not prepared,
                    trimmed_points=trimmed_points,
                )
            )
        return prepared

    def _on_mouse_moved(self, event) -> None:
        if not self._prepared_series or not self.plot_widget.isVisible():
            return
        pos = event[0]
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self.v_line.hide()
            self.hover_label.hide()
            return
        mouse_point = self.plot_widget.getPlotItem().vb.mapSceneToView(pos)
        x = mouse_point.x()
        nearest = self._nearest_points(x)
        if not nearest:
            return

        nearest_x = nearest[0][1]
        self.v_line.setPos(nearest_x)
        self.v_line.show()
        point_date = datetime.fromtimestamp(nearest_x).strftime("%d/%m/%Y")
        rows = [point_date]
        for label, _, y_value in nearest[:6]:
            rows.append(f"{label}: {y_value:.2f}")
        if len(nearest) > 6:
            rows.append(f"+{len(nearest) - 6} seri")
        self.hover_label.setText("\n".join(rows))
        view_range = self.plot_widget.getPlotItem().vb.viewRange()
        self.hover_label.setPos(x, view_range[1][1])
        self.hover_label.show()

    def _nearest_points(self, x: float) -> List[Tuple[str, float, float]]:
        result = []
        for series in self._prepared_series:
            if not series.x_values:
                continue
            idx = min(range(len(series.x_values)), key=lambda i: abs(series.x_values[i] - x))
            result.append((series.label, series.x_values[idx], series.y_values[idx]))
        result.sort(key=lambda item: abs(item[1] - x))
        return result

    def _clear_legend(self) -> None:
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_legend_row(self, series: PreparedSeries) -> None:
        start = series.y_values[0]
        end = series.y_values[-1]
        change = ((end - start) / start) * 100 if start else 0.0
        text = f"{series.label}\n{end:.2f}  ({change:+.1f}%)"
        self._add_legend_label(text, series.color, primary=series.is_primary)

    def _add_legend_label(self, text: str, color: str, primary: bool = False) -> None:
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet(
            f"color: {TEXT_PRIMARY if primary else TEXT_SECONDARY};"
            f"font-weight: {'700' if primary else '500'};"
            "background: transparent;"
            "border: none;"
            f"font-size: {'13px' if primary else '12px'};"
        )
        label.setProperty("seriesColor", color)
        label.setText(f"<span style='color:{color};'>■</span> {text.replace(chr(10), '<br>')}")
        self.legend_layout.addWidget(label)

    @staticmethod
    def _date_to_x(point_date: date) -> float:
        return datetime.combine(point_date, time.min).timestamp()
