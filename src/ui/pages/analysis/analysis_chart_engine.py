# src/ui/pages/analysis/analysis_chart_engine.py

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Qt5Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class AnalysisChartEngine(QWidget):
    """
    Analiz sayfasındaki çizim motoru.
    Çizgi serileri ve portföy dağılımı grafiklerini çizer.
    """

    def __init__(self, parent=None, show_toolbar: bool = True):
        super().__init__(parent)
        self._show_toolbar = show_toolbar
        self._init_ui()

    def _init_ui(self):
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.figure = Figure(figsize=(10, 6), facecolor="#0f172a")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumWidth(0)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setProperty("cssClass", "chartToolbar")
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if self._show_toolbar:
            layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.lbl_summary = QLabel("Grafik verisi bekleniyor")
        self.lbl_summary.setProperty("cssClass", "chartSummaryText")
        layout.addWidget(self.lbl_summary)

    def draw_empty_chart(self, message: str):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#0f172a")
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=14, color="#94a3b8", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        self.lbl_summary.setText(message)
        self.canvas.draw()

    def draw_line_series(
        self,
        title: str,
        y_label: str,
        series_map: Dict[str, Dict[date, Decimal | float]],
        normalize: bool = False,
        baseline: float | None = None,
    ):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#0f172a")

        colors = plt.cm.tab10.colors
        valid_count = 0

        for idx, (label, points) in enumerate(series_map.items()):
            if not points:
                continue
            x_values = sorted(points.keys())
            y_values = [float(points[d]) for d in x_values]
            if normalize:
                base = next((value for value in y_values if value > 0), None)
                if base is None:
                    continue
                y_values = [(value / base) * 100 for value in y_values]
            ax.plot(x_values, y_values, label=label, color=colors[idx % len(colors)], linewidth=2)
            valid_count += 1

        if valid_count == 0:
            self.draw_empty_chart("Veri bulunamadı")
            return

        if baseline is not None:
            ax.axhline(y=baseline, color="#94a3b8", linestyle="--", alpha=0.5)

        ax.set_title(title, color="#f1f5f9", fontsize=14, fontweight="bold")
        ax.set_xlabel("Tarih", color="#94a3b8")
        ax.set_ylabel(y_label, color="#94a3b8")
        ax.tick_params(colors="#94a3b8")
        ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9")
        ax.grid(True, alpha=0.3, color="#334155")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))

        for spine in ax.spines.values():
            spine.set_color("#334155")

        self.lbl_summary.setText(f"{valid_count} seri gösteriliyor")
        self.canvas.draw()

    def draw_portfolio_pie(self, title: str, breakdown: List[Tuple[str, float]]):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#0f172a")

        if not breakdown:
            self.draw_empty_chart("Portföyde pozisyon yok veya değer hesaplanamadı")
            return

        labels = [item[0] for item in breakdown]
        values = [item[1] for item in breakdown]
        colors = plt.cm.Set3.colors[: len(labels)]

        _, _, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors,
            textprops={"color": "#f1f5f9", "fontsize": 10},
        )

        for autotext in autotexts:
            autotext.set_color("#0f172a")
            autotext.set_fontweight("bold")

        ax.set_title(title, color="#f1f5f9", fontsize=14, fontweight="bold")
        total = sum(values)
        self.lbl_summary.setText(f"Toplam {len(breakdown)} pozisyon, ₺{total:,.2f}")
        self.canvas.draw()

    def save_chart(self, file_path: str):
        self.figure.savefig(file_path, facecolor="#0f172a", edgecolor="none", bbox_inches="tight", dpi=150)
