from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict

from PyQt5.QtWidgets import QFileDialog, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.application.services.analysis import ComparisonViewDTO
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared import MetricCard

from .analysis_chart_engine import AnalysisChartEngine


class AnalysisComparisonSection(QWidget):
    MODE_PORTFOLIO = "portfolio_benchmark"
    MODE_PORTFOLIOS = "portfolio_portfolios"
    MODE_STOCKS = "stocks_portfolio"
    MODE_STOCKS_ONLY = "stocks_only"
    MODE_RELATIVE = "relative_gap"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dto: ComparisonViewDTO | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        self.warning_banner = QLabel("")
        self.warning_banner.setProperty("cssClass", "warningBanner")
        self.warning_banner.setWordWrap(True)
        self.warning_banner.hide()
        layout.addWidget(self.warning_banner)

        top_panel = QFrame()
        top_panel.setProperty("cssClass", "panelFramePadded")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(15, 15, 15, 15)
        top_layout.setSpacing(12)

        lbl_mode = QLabel("Grafik Modu")
        lbl_mode.setProperty("cssClass", "panelTitle")
        top_layout.addWidget(lbl_mode)

        self.combo_mode = QComboBox()
        self.combo_mode.setProperty("cssClass", "customComboBox")
        self.combo_mode.addItem("Portföy vs Benchmark", self.MODE_PORTFOLIO)
        self.combo_mode.addItem("Portföyler Arası", self.MODE_PORTFOLIOS)
        self.combo_mode.addItem("Hisseler vs Portföy", self.MODE_STOCKS)
        self.combo_mode.addItem("Hisseler Arası", self.MODE_STOCKS_ONLY)
        self.combo_mode.addItem("Göreli Fark", self.MODE_RELATIVE)
        self.combo_mode.currentIndexChanged.connect(self._redraw_chart)
        top_layout.addWidget(self.combo_mode)
        top_layout.addStretch()

        self.btn_save = QPushButton("Grafiği Kaydet")
        self.btn_save.setProperty("cssClass", "secondaryButton")
        self.btn_save.setIcon(IconManager.get_icon("save", color="@COLOR_TEXT_PRIMARY"))
        self.btn_save.clicked.connect(self._save_chart)
        top_layout.addWidget(self.btn_save)
        layout.addWidget(top_panel)

        self.metrics_layout = QHBoxLayout()
        self.metrics_layout.setSpacing(15)
        layout.addLayout(self.metrics_layout)

        self.chart_engine = AnalysisChartEngine(show_toolbar=True)
        layout.addWidget(self.chart_engine)

    def set_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.chart_engine.draw_empty_chart(message)

    def set_data(self, dto: ComparisonViewDTO) -> None:
        self._dto = dto
        if dto.warnings:
            self.warning_banner.setText(" | ".join(dto.warnings))
            self.warning_banner.show()
        else:
            self.warning_banner.hide()
        self._rebuild_metric_cards(dto)
        self._redraw_chart()

    def _rebuild_metric_cards(self, dto: ComparisonViewDTO) -> None:
        while self.metrics_layout.count():
            item = self.metrics_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for metric in dto.comparison_metrics:
            card = MetricCard(metric.label, icon_name="scale")
            card.update(
                current="—" if metric.portfolio_return_pct is None else f"%{metric.portfolio_return_pct:+.2f}",
                optimal="—" if metric.benchmark_return_pct is None else f"%{metric.benchmark_return_pct:+.2f}",
                delta=metric.relative_gap_pct or 0.0,
                positive_is_good=True,
            )
            self.metrics_layout.addWidget(card, 1)
        self.metrics_layout.addStretch()

    def _redraw_chart(self) -> None:
        if self._dto is None:
            self.chart_engine.draw_empty_chart("Karşılaştırma verisi bekleniyor.")
            return

        mode = self.combo_mode.currentData()
        if mode == self.MODE_PORTFOLIO:
            series_map: Dict[str, Dict[date, Decimal | float]] = {self._dto.current_portfolio_label: self._dto.portfolio_series}
            for benchmark in self._dto.benchmark_series:
                series_map[benchmark.label] = benchmark.points
            self.chart_engine.draw_line_series(
                title="Portföy ve Benchmark Karşılaştırması",
                y_label="Normalize Değer",
                series_map=series_map,
                normalize=True,
                baseline=100,
            )
        elif mode == self.MODE_PORTFOLIOS:
            series_map = {self._dto.current_portfolio_label: self._dto.portfolio_series}
            for portfolio in self._dto.comparison_portfolios:
                series_map[portfolio.label] = portfolio.points
            self.chart_engine.draw_line_series(
                title="Portföyler Arası Karşılaştırma",
                y_label="Normalize Değer",
                series_map=series_map,
                normalize=True,
                baseline=100,
            )
        elif mode == self.MODE_STOCKS:
            series_map = {self._dto.current_portfolio_label: self._dto.portfolio_series}
            series_map.update(self._dto.stock_series)
            self.chart_engine.draw_line_series(
                title="Seçili Hisseler ve Portföy",
                y_label="Normalize Değer",
                series_map=series_map,
                normalize=True,
                baseline=100,
            )
        elif mode == self.MODE_STOCKS_ONLY:
            series_map = dict(self._dto.stock_series)
            if not series_map:
                self.chart_engine.draw_empty_chart("Karşılaştırılacak hisse verisi bulunamadı.")
                return
            title = "Seçili Hisseler Karşılaştırması" if len(series_map) > 1 else f"{next(iter(series_map))} Performansı"
            self.chart_engine.draw_line_series(
                title=title,
                y_label="Normalize Değer",
                series_map=series_map,
                normalize=True,
                baseline=100,
            )
        else:
            series_map = {}
            for benchmark in self._dto.benchmark_series:
                aligned = self._build_relative_gap_series(self._dto.portfolio_series, benchmark.points)
                if aligned:
                    series_map[f"{self._dto.current_portfolio_label} - {benchmark.label}"] = aligned
            for portfolio in self._dto.comparison_portfolios:
                aligned = self._build_relative_gap_series(self._dto.portfolio_series, portfolio.points)
                if aligned:
                    series_map[f"{self._dto.current_portfolio_label} - {portfolio.label}"] = aligned
            self.chart_engine.draw_line_series(
                title="Göreli Fark Karşılaştırması",
                y_label="Fark (%)",
                series_map=series_map,
                normalize=False,
                baseline=0,
            )

    def _build_relative_gap_series(
        self,
        portfolio_series: Dict[date, Decimal],
        benchmark_series: Dict[date, Decimal],
    ) -> Dict[date, float]:
        result: Dict[date, float] = {}
        portfolio_base = next((float(value) for value in portfolio_series.values() if value and value > 0), None)
        benchmark_base = next((float(value) for value in benchmark_series.values() if value and value > 0), None)
        if portfolio_base is None or benchmark_base is None:
            return result
        for point_date, portfolio_value in portfolio_series.items():
            benchmark_value = benchmark_series.get(point_date)
            if benchmark_value is None:
                continue
            portfolio_norm = (float(portfolio_value) / portfolio_base) * 100
            benchmark_norm = (float(benchmark_value) / benchmark_base) * 100
            result[point_date] = portfolio_norm - benchmark_norm
        return result

    def _save_chart(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Grafiği Kaydet",
            "analiz_karsilastirma.png",
            "PNG Dosyası (*.png);;PDF Dosyası (*.pdf);;SVG Dosyası (*.svg)",
        )
        if file_path:
            self.chart_engine.save_chart(file_path)
