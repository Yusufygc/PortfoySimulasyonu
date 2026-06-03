from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict

from PyQt5.QtWidgets import QFileDialog, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy, QScrollArea
from PyQt5.QtCore import Qt

from src.application.services.analysis import ComparisonViewDTO
from src.ui.formatters import display_ticker
from src.ui.widgets.shared import MetricCard
from src.ui.widgets.shared.controls.animated_button import AnimatedButton

from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
import pandas as pd
from .chart_builder import build_performance_line_chart_v2, patch_plotly_html


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

        self.btn_save = AnimatedButton("Grafiği Kaydet")
        self.btn_save.setProperty("cssClass", "secondaryButton")
        self.btn_save.setIconName("save", color="@COLOR_TEXT_PRIMARY", size=24)
        self.btn_save.clicked.connect(self._save_chart)
        top_layout.addWidget(self.btn_save)
        layout.addWidget(top_panel)

        # Metrik kartları için yatay kaydırılabilir alan
        self.metrics_scroll = QScrollArea()
        self.metrics_scroll.setWidgetResizable(True)
        self.metrics_scroll.setFrameShape(QFrame.NoFrame)
        self.metrics_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.metrics_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.metrics_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.metrics_scroll.setFixedHeight(125) # Kartların sığacağı sabit yükseklik
        
        self.metrics_container = QWidget()
        self.metrics_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        self.metrics_layout = QHBoxLayout(self.metrics_container)
        self.metrics_layout.setContentsMargins(0, 0, 0, 0)
        self.metrics_layout.setSpacing(12)
        
        self.metrics_scroll.setWidget(self.metrics_container)
        layout.addWidget(self.metrics_scroll)

        self.chart_engine = SilentWebEngineView()
        self.chart_engine.setMinimumHeight(500)
        self.chart_engine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.chart_engine)

    def set_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.chart_engine.setHtml(f"<div style='color:white; text-align:center; padding-top:200px;'>{message}</div>")

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
            card.setMinimumWidth(180) # Sıkışmayı önlemek için minimum genişlik veriyoruz
            card.setMaximumWidth(240)
            card.update(
                current="—" if metric.portfolio_return_pct is None else f"%{metric.portfolio_return_pct:+.2f}",
                optimal="—" if metric.benchmark_return_pct is None else f"%{metric.benchmark_return_pct:+.2f}",
                delta=metric.relative_gap_pct or 0.0,
                positive_is_good=True,
            )
            self.metrics_layout.addWidget(card)
        self.metrics_layout.addStretch()

    def _redraw_chart(self) -> None:
        if self._dto is None:
            self.chart_engine.setHtml("<div style='color:white; text-align:center; padding-top:200px;'>Karşılaştırma verisi bekleniyor.</div>")
            return

        mode = self.combo_mode.currentData()
        
        # Convert dict to pd.Series for Plotly builder
        if not self._dto.portfolio_series:
            self.chart_engine.setHtml("<div style='color:white; text-align:center; padding-top:200px;'>Portföy verisi bulunamadı.</div>")
            return
            
        p_series = pd.Series({pd.Timestamp(d): float(v) for d, v in self._dto.portfolio_series.items()})
        p_series.name = "Portföy"
        
        currency_label = "TL/USD/REAL" # TODO: get this from DTO
        
        if mode == self.MODE_PORTFOLIO:
            b_data = {}
            for benchmark in self._dto.benchmark_series:
                b_data[benchmark.label] = {pd.Timestamp(d): float(v) for d, v in benchmark.points.items()}
            b_df = pd.DataFrame(b_data)
            
            fig = build_performance_line_chart_v2(
                portfolio_series=p_series,
                benchmark_series=b_df,
                currency_label=currency_label,
                title="Portföy ve Benchmark Karşılaştırması",
            )
            self._set_fig_to_view(fig)
            
        elif mode == self.MODE_PORTFOLIOS:
            b_data = {}
            for portfolio in self._dto.comparison_portfolios:
                b_data[portfolio.label] = {pd.Timestamp(d): float(v) for d, v in portfolio.points.items()}
            b_df = pd.DataFrame(b_data)
            
            fig = build_performance_line_chart_v2(
                portfolio_series=p_series,
                benchmark_series=b_df,
                currency_label=currency_label,
                title="Portföyler Arası Karşılaştırma",
            )
            self._set_fig_to_view(fig)
            
        elif mode == self.MODE_STOCKS:
            b_data = {}
            for label, series in self._dto.stock_series.items():
                b_data[display_ticker(label)] = {pd.Timestamp(d): float(v) for d, v in series.items()}
            b_df = pd.DataFrame(b_data)
            
            fig = build_performance_line_chart_v2(
                portfolio_series=p_series,
                benchmark_series=b_df,
                currency_label=currency_label,
                title="Seçili Hisseler ve Portföy",
            )
            self._set_fig_to_view(fig)
            
        elif mode == self.MODE_STOCKS_ONLY:
            if not self._dto.stock_series:
                self.chart_engine.setHtml("<div style='color:white; text-align:center; padding-top:200px;'>Hisse verisi bulunamadı.</div>")
                return
            b_data = {}
            for label, series in self._dto.stock_series.items():
                b_data[display_ticker(label)] = {pd.Timestamp(d): float(v) for d, v in series.items()}
            b_df = pd.DataFrame(b_data)
            
            fig = build_performance_line_chart_v2(
                portfolio_series=None,
                benchmark_series=b_df,
                currency_label=currency_label,
                title="Seçili Hisseler Karşılaştırması",
            )
            self._set_fig_to_view(fig)
            
        else:
            # MODE_RELATIVE
            b_data = {}
            for benchmark in self._dto.benchmark_series:
                aligned = self._build_relative_gap_series(self._dto.portfolio_series, benchmark.points)
                if aligned:
                    b_data[f"{self._dto.current_portfolio_label} - {benchmark.label}"] = {pd.Timestamp(d): float(v) for d, v in aligned.items()}
                    
            for portfolio in self._dto.comparison_portfolios:
                aligned = self._build_relative_gap_series(self._dto.portfolio_series, portfolio.points)
                if aligned:
                    b_data[f"{self._dto.current_portfolio_label} - {portfolio.label}"] = {pd.Timestamp(d): float(v) for d, v in aligned.items()}
                    
            b_df = pd.DataFrame(b_data)
            fig = build_performance_line_chart_v2(
                portfolio_series=None,
                benchmark_series=b_df,
                currency_label="Fark (%)",
                title="Göreli Fark Karşılaştırması",
            )
            # Override baseline since it's gap
            fig.update_yaxes(title_text="Fark (%)")
            self._set_fig_to_view(fig)

    def _set_fig_to_view(self, fig):
        html = fig.to_html(include_plotlyjs=True)
        html = patch_plotly_html(html)
        if not hasattr(self, "_temp_file_path") or self._temp_file_path is None:
            import tempfile
            f = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
            self._temp_file_path = f.name
            f.close()
            
        with open(self._temp_file_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        from PyQt5.QtCore import QUrl
        self.chart_engine.load(QUrl.fromLocalFile(self._temp_file_path))

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
            # QWebEngineView save functionality requires calling page().printToPdf or snapshot.
            # For simplicity here, we could take a widget grab
            self.chart_engine.grab().save(file_path)
