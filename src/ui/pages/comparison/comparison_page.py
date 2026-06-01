from __future__ import annotations
import os
import tempfile
import logging
from datetime import date, timedelta
import pandas as pd
import numpy as np
from PyQt5.QtCore import QUrl, Qt, QThreadPool
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go

from src.ui.pages.base_page import BasePage
from src.ui.worker import Worker
from src.application.services.analysis.models import AnalysisFilterState
from src.application.services.analysis.comparison_service import ComparisonService
from src.ui.pages.comparison.chart_factory import ComparisonChartFactory
from src.ui.pages.comparison.widgets.ribbon_bar import ComparisonRibbonBar
from src.ui.pages.analysis.chart_builder import patch_plotly_html

logger = logging.getLogger(__name__)

class ComparisonPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Karşılaştırma Laboratuvarı"
        self.analysis_service = container.analysis_service
        self.threadpool = QThreadPool.globalInstance()
        self._request_seq = 0
        self._temp_files = []
        self._init_ui()
        self._load_initial_options()

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Üst Başlık ve Açıklama
        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        
        lbl_title = QLabel("Karşılaştırma Laboratuvarı")
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)
        
        lbl_desc = QLabel("Varlıkları, benchmarkları ve portföyleri rasyo, drawdown ve risk-getiri bazında kıyaslayın.")
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)
        
        header_layout.addLayout(title_col)
        layout.addLayout(header_layout)
        
        # 1. Ribbon Bar
        self.ribbon_bar = ComparisonRibbonBar()
        self.ribbon_bar.filter_changed.connect(self._request_refresh)
        layout.addWidget(self.ribbon_bar)
        
        # 2. Scroll Area (Tüm Grafiklerin Dikey Listesi)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 10, 0, 0)
        scroll_layout.setSpacing(20) # Grafikler arası boşluk
        
        # 1. Ana Performans Kıyaslama Grafiği
        self.main_chart_view = QWebEngineView()
        self.main_chart_view.setMinimumHeight(600)
        scroll_layout.addWidget(self.main_chart_view)
        
        # 2. Dönem Sonu Getiri Özeti Tablosu (Yerel QTableWidget)
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels([
            "Varlık Adı", "Başlangıç Değeri", "Dönem Sonu Değeri", "Toplam Getiri %"
        ])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.summary_table.setSelectionMode(QTableWidget.NoSelection)
        self.summary_table.setFocusPolicy(Qt.NoFocus)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setMinimumHeight(300)
        self.summary_table.setMaximumHeight(400)
        self.summary_table.setProperty("cssClass", "summaryTable")
        scroll_layout.addWidget(self.summary_table)
        
        # 3. Maksimum Drawdown Analizi Grafiği
        self.drawdown_chart_view = QWebEngineView()
        self.drawdown_chart_view.setMinimumHeight(600)
        scroll_layout.addWidget(self.drawdown_chart_view)
        
        # 4. Dönemsel Getiri Karşılaştırması Grafiği
        self.periodic_chart_view = QWebEngineView()
        self.periodic_chart_view.setMinimumHeight(600)
        scroll_layout.addWidget(self.periodic_chart_view)
        
        # 5. Risk-Getiri Dağılımı Grafiği
        self.scatter_chart_view = QWebEngineView()
        self.scatter_chart_view.setMinimumHeight(600)
        scroll_layout.addWidget(self.scatter_chart_view)
        
        # 6. Treemap (Getiri Katkı Haritası) Grafiği
        self.treemap_chart_view = QWebEngineView()
        self.treemap_chart_view.setMinimumHeight(600)
        scroll_layout.addWidget(self.treemap_chart_view)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

    def on_page_enter(self) -> None:
        self._load_initial_options()
        self._request_refresh()

    def _load_initial_options(self) -> None:
        # Load asset choices: Portfolios + Benchmarks + Stocks
        assets = []
        
        # Portfolios
        portfolios = self.analysis_service.get_portfolio_options()
        for p in portfolios:
            assets.append((p.label, p.code))
            
        # Benchmarks
        benchmarks = self.analysis_service.get_benchmark_definitions()
        for b in benchmarks:
            assets.append((b.label, b.code))
            
        self.ribbon_bar.set_assets(assets)

    def _request_refresh(self) -> None:
        start_date, end_date = self.ribbon_bar.date_range()
        selected_codes = self.ribbon_bar.selected_assets()
        
        if not selected_codes:
            self._render_empty_state("Lütfen kıyaslanacak varlıkları seçin.")
            return
            
        self._request_seq += 1
        request_id = self._request_seq
        
        portfolio_sources = []
        benchmarks = []
        stock_ids = []
        
        for code in selected_codes:
            if code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:"):
                portfolio_sources.append(code)
            elif code in ["bist100", "gold", "usd", "eur", "deposit", "cpi", "try"]:
                benchmarks.append(code)
            else:
                try:
                    stock_ids.append(int(code))
                except ValueError:
                    pass
                    
        primary_source = portfolio_sources[0] if portfolio_sources else "dashboard"
        
        filter_state = AnalysisFilterState(
            start_date=start_date,
            end_date=end_date,
            selected_stock_ids=stock_ids,
            selected_benchmarks=benchmarks,
            portfolio_source=primary_source,
            comparison_portfolio_sources=portfolio_sources,
            currency_mode="TL"
        )
        
        worker = Worker(self.analysis_service.get_comparison_view, filter_state)
        worker.signals.result.connect(lambda result, rid=request_id: self._on_data_ready(rid, result))
        worker.signals.error.connect(lambda err, rid=request_id: self._on_data_error(rid, err))
        self.threadpool.start(worker)

    def _on_data_ready(self, request_id: int, dto) -> None:
        if request_id != self._request_seq:
            return
            
        series_dict = {}
        self.code_to_label = {}
        
        # Primary portfolio
        if dto.portfolio_series:
            p_series = pd.Series({pd.Timestamp(d): float(v) for d, v in dto.portfolio_series.items()})
            p_series.name = dto.current_portfolio_label
            series_dict[dto.current_portfolio_label] = p_series
            self.code_to_label["dashboard"] = dto.current_portfolio_label
            
        # Comparison portfolios
        for cp in dto.comparison_portfolios:
            if cp.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in cp.points.items()})
                s.name = cp.label
                series_dict[cp.label] = s
                self.code_to_label[cp.code] = cp.label
                self.code_to_label[f"portfolio:{cp.code}"] = cp.label
                
        # Benchmarks
        for b in dto.benchmark_series:
            if b.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in b.points.items()})
                s.name = b.label
                series_dict[b.label] = s
                self.code_to_label[b.code] = b.label
                
        # Stocks
        for stock_id, points in dto.stock_series.items():
            if points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in points.items()})
                s.name = str(stock_id)
                series_dict[s.name] = s
                self.code_to_label[str(stock_id)] = s.name
                
        if not series_dict:
            self._render_empty_state("Seçilen filtreler için veri bulunamadı.")
            return
            
        # Align series
        aligned_df = ComparisonService.align_financial_series(series_dict)
        
        # Render charts
        self._render_charts(aligned_df)

    def _on_data_error(self, request_id: int, err_tuple) -> None:
        if request_id != self._request_seq:
            return
        self._render_empty_state(f"Veri yükleme hatası: {err_tuple[1]}")

    def _render_charts(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
            
        mode = self.ribbon_bar.selected_mode()
        
        # Build Main Chart
        fig_main = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        if mode == "Normalize (Baz 100)":
            df_norm = df.copy()
            for col in df_norm.columns:
                base_val = df_norm[col].iloc[0]
                if base_val != 0:
                    df_norm[col] = (df_norm[col] / base_val) * 100.0
            for i, col in enumerate(df_norm.columns):
                color = colors_palette[i % len(colors_palette)]
                fig_main.add_trace(go.Scatter(x=df_norm.index, y=df_norm[col], name=col, line=dict(width=2, color=color)))
            ComparisonChartFactory._apply_theme_layout(fig_main, "Normalize Performans Kıyaslaması (Baz 100)")
        elif mode == "Rasyo Modu":
            num_code, den_code = self.ribbon_bar.ratio_assets()
            num_col = self._find_column_by_code(df, num_code)
            den_col = self._find_column_by_code(df, den_code)
            
            if num_col and den_col:
                ratio_series = ComparisonService.calculate_asset_ratio(df[num_col], df[den_col])
                fig_main.add_trace(go.Scatter(x=ratio_series.index, y=ratio_series.values, name=f"{num_col} / {den_col}", line=dict(width=2, color="#00D4FF")))
                ComparisonChartFactory._apply_theme_layout(fig_main, f"Rasyo Gösterimi: {num_col} / {den_col}")
            else:
                for i, col in enumerate(df.columns):
                    color = colors_palette[i % len(colors_palette)]
                    fig_main.add_trace(go.Scatter(x=df.index, y=df[col], name=col, line=dict(width=2, color=color)))
                ComparisonChartFactory._apply_theme_layout(fig_main, "Performans Kıyaslaması")
        else:
            df_ret = df.copy()
            for col in df_ret.columns:
                base_val = df_ret[col].iloc[0]
                df_ret[col] = ((df_ret[col] - base_val) / base_val) * 100.0 if base_val != 0 else 0.0
            for i, col in enumerate(df_ret.columns):
                color = colors_palette[i % len(colors_palette)]
                fig_main.add_trace(go.Scatter(x=df_ret.index, y=df_ret[col], name=col, line=dict(width=2, color=color)))
            ComparisonChartFactory._apply_theme_layout(fig_main, "Kümülatif Performans Getirisi (%)")
            
        self._load_plotly_to_view(self.main_chart_view, fig_main)
        
        # Build Summary Table (PyQt5 QTableWidget)
        self.summary_table.setRowCount(0)
        self.summary_table.setRowCount(len(df.columns))
        
        for row, col in enumerate(df.columns):
            series = df[col].dropna()
            if not series.empty:
                start_val = float(series.iloc[0])
                end_val = float(series.iloc[-1])
                tot_ret = ((end_val - start_val) / start_val) * 100.0 if start_val != 0.0 else 0.0
                
                item_name = QTableWidgetItem(col)
                item_start = QTableWidgetItem(f"{start_val:,.2f}")
                item_end = QTableWidgetItem(f"{end_val:,.2f}")
                
                sign = "+" if tot_ret > 0 else ""
                item_ret = QTableWidgetItem(f"{sign}{tot_ret:.2f}%")
                
                item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item_start.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_end.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_ret.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                if tot_ret > 0:
                    item_ret.setForeground(QBrush(QColor("#10b981")))
                elif tot_ret < 0:
                    item_ret.setForeground(QBrush(QColor("#ef4444")))
                else:
                    item_ret.setForeground(QBrush(QColor("#94a3b8")))
                    
                self.summary_table.setItem(row, 0, item_name)
                self.summary_table.setItem(row, 1, item_start)
                self.summary_table.setItem(row, 2, item_end)
                self.summary_table.setItem(row, 3, item_ret)
        
        # Build Drawdowns
        df_dd = ComparisonService.calculate_drawdowns(df)
        fig_dd = ComparisonChartFactory.build_drawdown_chart(df_dd)
        self._load_plotly_to_view(self.drawdown_chart_view, fig_dd)
        
        # Build Periodic Returns
        df_periodic = ComparisonService.calculate_periodic_returns(df, freq="ME")
        fig_periodic = ComparisonChartFactory.build_period_bar_chart(df_periodic)
        self._load_plotly_to_view(self.periodic_chart_view, fig_periodic)
        
        # Build Risk-Return Scatter
        metrics = ComparisonService.calculate_risk_return_metrics(df)
        scatter_data = []
        for name, m in metrics.items():
            scatter_data.append({
                "Volatilite %": m["annual_volatility_pct"],
                "Getiri %": m["total_return_pct"],
                "Varlık": name
            })
        df_scatter = pd.DataFrame(scatter_data).set_index("Varlık")
        fig_scatter = ComparisonChartFactory.build_risk_return_scatter(df_scatter)
        self._load_plotly_to_view(self.scatter_chart_view, fig_scatter)
        
        # Build Treemap
        weights = [max(abs(m["total_return_pct"]), 1.0) for m in metrics.values()]
        df_weights = pd.DataFrame({
            "Varlık Ağırlığı %": weights,
            "Getiri %": [tot_ret["total_return_pct"] for tot_ret in metrics.values()]
        }, index=df.columns)
        fig_tree = ComparisonChartFactory.build_treemap(df_weights)
        self._load_plotly_to_view(self.treemap_chart_view, fig_tree)

    def _find_column_by_code(self, df: pd.DataFrame, code: str) -> str | None:
        if not hasattr(self, "code_to_label"):
            self.code_to_label = {}
            
        label = self.code_to_label.get(code)
        if label and label in df.columns:
            return label
            
        for col in df.columns:
            if col.lower() == code.lower():
                return col
            if code.isdigit() and col == code:
                return col
            if code.lower().replace(" ", "").replace("_", "") in col.lower().replace(" ", "").replace("_", ""):
                return col
        return df.columns[0] if not df.empty else None

    def _load_plotly_to_view(self, view: QWebEngineView, fig: go.Figure) -> None:
        html = fig.to_html(include_plotlyjs=True)
        html = patch_plotly_html(html)
        
        f = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        f.write(html)
        f.close()
        
        self._temp_files.append(f.name)
        view.load(QUrl.fromLocalFile(f.name))

    def _render_empty_state(self, message: str) -> None:
        empty_html = f"""
        <html>
        <body style="background-color:#0f172a; color:#94a3b8; font-family:Segoe UI, sans-serif; text-align:center; padding-top:150px;">
            <h3>{message}</h3>
        </body>
        </html>
        """
        self.main_chart_view.setHtml(empty_html)
        self.summary_table.setRowCount(0)
        self.drawdown_chart_view.setHtml(empty_html)
        self.periodic_chart_view.setHtml(empty_html)
        self.scatter_chart_view.setHtml(empty_html)
        self.treemap_chart_view.setHtml(empty_html)

    def closeEvent(self, event) -> None:
        for path in self._temp_files:
            try:
                os.remove(path)
            except OSError:
                pass
        super().closeEvent(event)
