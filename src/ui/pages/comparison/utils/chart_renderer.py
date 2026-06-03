# src/ui/pages/comparison/utils/chart_renderer.py
"""Karşılaştırma sayfasındaki tüm grafik ve tablo render işlemleri."""
from __future__ import annotations

import logging
import os
import tempfile
from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objects as go
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QBrush, QColor
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
from PyQt5.QtWidgets import QTableWidgetItem

from src.application.services.analysis.comparison_service import ComparisonService
from src.ui.pages.comparison.chart_factory import ComparisonChartFactory
from src.ui.pages.comparison.utils.plotly_html import build_plotly_html, ensure_patched_plotly_js

if TYPE_CHECKING:
    from src.ui.pages.comparison.comparison_page import ComparisonPage

logger = logging.getLogger(__name__)

_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]

_EMPTY_HTML = """
<html>
<body style="background-color:#0f172a; color:#94a3b8;
             font-family:Segoe UI, sans-serif; text-align:center; padding-top:150px;">
    <h3>{message}</h3>
</body>
</html>
"""


class ChartRenderer:
    """Plotly grafiklerini, QTableWidget içeriğini ve boş durumu yönetir."""

    def __init__(self, page: ComparisonPage) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # Toplu render
    # ------------------------------------------------------------------

    def render_charts(self, df: pd.DataFrame) -> None:
        """DataFrame'den tüm grafikleri override'lara göre render eder."""
        if df.empty:
            return
        page = self.page
        mode = page.ribbon_bar.selected_mode()
        df_metrics = df if mode == "Rasyo Modu" else df

        if not page.chart_overrides.get("main_chart"):
            self.render_main_chart(df)
        if not page.chart_overrides.get("summary_table"):
            self.render_summary_table(df_metrics)
        if not page.chart_overrides.get("drawdown_chart"):
            self.render_drawdown_chart(df_metrics)
        if not page.chart_overrides.get("periodic_chart"):
            self.render_periodic_chart(df_metrics)
        if not page.chart_overrides.get("scatter_chart"):
            self.render_scatter_chart(df_metrics)
        if not page.chart_overrides.get("treemap_chart"):
            self.render_treemap_chart(df_metrics)

    def render_single_chart(self, chart_key: str, df: pd.DataFrame) -> None:
        """Belirli bir grafik key'ine göre tek grafiği render eder."""
        if df.empty:
            return
        dispatch = {
            "main_chart":     self.render_main_chart,
            "summary_table":  self.render_summary_table,
            "drawdown_chart": self.render_drawdown_chart,
            "periodic_chart": self.render_periodic_chart,
            "scatter_chart":  self.render_scatter_chart,
            "treemap_chart":  self.render_treemap_chart,
        }
        handler = dispatch.get(chart_key)
        if handler:
            handler(df)

    # ------------------------------------------------------------------
    # Ana performans grafiği
    # ------------------------------------------------------------------

    def render_main_chart(self, df: pd.DataFrame) -> None:
        """Kümülatif / normalize / rasyo modunda ana performans grafiğini çizer."""
        if df.empty:
            return
        page = self.page
        mode = page.ribbon_bar.selected_mode()
        fig = go.Figure()

        if mode == "Normalize (Baz 100)":
            df_norm = df.copy()
            for col in df_norm.columns:
                base_val = df_norm[col].iloc[0]
                if base_val != 0:
                    df_norm[col] = (df_norm[col] / base_val) * 100.0
            for i, col in enumerate(df_norm.columns):
                fig.add_trace(go.Scatter(
                    x=df_norm.index, y=df_norm[col], name=col,
                    line=dict(width=2, color=_COLORS[i % len(_COLORS)])
                ))
            ComparisonChartFactory._apply_theme_layout(fig, "Normalize Performans Kıyaslaması (Baz 100)")

        elif mode == "Rasyo Modu":
            num_code, den_code = page.ribbon_bar.ratio_assets()
            num_col = page._data_manager.find_column_by_code(df, num_code)
            den_col = page._data_manager.find_column_by_code(df, den_code)
            if num_col and den_col:
                ratio_series = ComparisonService.calculate_asset_ratio(df[num_col], df[den_col])
                ratio_name = f"{num_col} / {den_col}"
                fig.add_trace(go.Scatter(
                    x=ratio_series.index, y=ratio_series.values,
                    name=ratio_name, line=dict(width=2, color="#00D4FF")
                ))
                ComparisonChartFactory._apply_theme_layout(fig, f"Rasyo Gösterimi: {ratio_name}")
            else:
                for i, col in enumerate(df.columns):
                    fig.add_trace(go.Scatter(
                        x=df.index, y=df[col], name=col,
                        line=dict(width=2, color=_COLORS[i % len(_COLORS)])
                    ))
                ComparisonChartFactory._apply_theme_layout(fig, "Performans Kıyaslaması")

        else:
            df_ret = df.copy()
            for col in df_ret.columns:
                base_val = df_ret[col].iloc[0]
                df_ret[col] = (
                    ((df_ret[col] - base_val) / base_val) * 100.0
                    if base_val != 0 else 0.0
                )
            for i, col in enumerate(df_ret.columns):
                fig.add_trace(go.Scatter(
                    x=df_ret.index, y=df_ret[col], name=col,
                    line=dict(width=2, color=_COLORS[i % len(_COLORS)])
                ))
            ComparisonChartFactory._apply_theme_layout(fig, "Kümülatif Performans Getirisi (%)")

        self._load_plotly_to_view(page.main_chart_view, fig)

    # ------------------------------------------------------------------
    # Özet tablo
    # ------------------------------------------------------------------

    def render_summary_table(self, df: pd.DataFrame) -> None:
        """Dönem özeti tablosunu doldurur."""
        if df.empty:
            return
        table = self.page.summary_table
        table.setRowCount(0)
        table.setRowCount(len(df.columns))

        for row, col in enumerate(df.columns):
            series = df[col].dropna()
            if series.empty:
                continue
            start_val = float(series.iloc[0])
            end_val = float(series.iloc[-1])
            tot_ret = ((end_val - start_val) / start_val * 100.0) if start_val != 0.0 else 0.0
            sign = "+" if tot_ret > 0 else ""
            items = [
                QTableWidgetItem(col),
                QTableWidgetItem(f"{start_val:,.2f}"),
                QTableWidgetItem(f"{end_val:,.2f}"),
                QTableWidgetItem(f"{sign}{tot_ret:.2f}%"),
            ]
            for item in items:
                item.setTextAlignment(Qt.AlignCenter)
            if tot_ret > 0:
                items[3].setForeground(QBrush(QColor("#10b981")))
            elif tot_ret < 0:
                items[3].setForeground(QBrush(QColor("#ef4444")))
            else:
                items[3].setForeground(QBrush(QColor("#94a3b8")))
            for col_idx, item in enumerate(items):
                table.setItem(row, col_idx, item)

        self._update_table_height()

    def _update_table_height(self) -> None:
        """Tablo yüksekliğini içeriğe göre ayarlar."""
        table = self.page.summary_table
        row_count = table.rowCount()
        header_height = table.horizontalHeader().height() or 38
        total_row_height = sum(table.rowHeight(i) or 36 for i in range(row_count))
        if total_row_height == 0 and row_count > 0:
            total_row_height = row_count * 36
        total_height = header_height + total_row_height + 4
        table.setMinimumHeight(total_height)
        table.setMaximumHeight(total_height)
        table.updateGeometry()

    # ------------------------------------------------------------------
    # Diğer grafikler
    # ------------------------------------------------------------------

    def render_drawdown_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df_dd = ComparisonService.calculate_drawdowns(df)
        fig = ComparisonChartFactory.build_drawdown_chart(df_dd)
        self._load_plotly_to_view(self.page.drawdown_chart_view, fig)

    def render_periodic_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df_periodic = ComparisonService.calculate_periodic_returns(df, freq="ME")
        fig = ComparisonChartFactory.build_period_bar_chart(df_periodic)
        self._load_plotly_to_view(self.page.periodic_chart_view, fig)

    def render_scatter_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        metrics = ComparisonService.calculate_risk_return_metrics(df)
        scatter_data = [
            {"Volatilite %": m["annual_volatility_pct"], "Getiri %": m["total_return_pct"], "Varlık": name}
            for name, m in metrics.items()
        ]
        df_scatter = pd.DataFrame(scatter_data).set_index("Varlık")
        fig = ComparisonChartFactory.build_risk_return_scatter(df_scatter)
        self._load_plotly_to_view(self.page.scatter_chart_view, fig)

    def render_treemap_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        metrics = ComparisonService.calculate_risk_return_metrics(df)
        weights = [max(abs(m["total_return_pct"]), 1.0) for m in metrics.values()]
        df_weights = pd.DataFrame(
            {"Varlık Ağırlığı %": weights, "Getiri %": [m["total_return_pct"] for m in metrics.values()]},
            index=df.columns,
        )
        fig = ComparisonChartFactory.build_treemap(df_weights)
        self._load_plotly_to_view(self.page.treemap_chart_view, fig)

    # ------------------------------------------------------------------
    # Boş durum
    # ------------------------------------------------------------------

    def render_empty_state(self, message: str) -> None:
        page = self.page
        empty_html = _EMPTY_HTML.format(message=message)
        page.main_chart_view.setHtml(empty_html)
        page.summary_table.setRowCount(0)
        page.drawdown_chart_view.setHtml(empty_html)
        page.periodic_chart_view.setHtml(empty_html)
        page.scatter_chart_view.setHtml(empty_html)
        page.treemap_chart_view.setHtml(empty_html)

    # ------------------------------------------------------------------
    # Plotly HTML yükleme
    # ------------------------------------------------------------------

    def _load_plotly_to_view(self, view: SilentWebEngineView, fig: go.Figure) -> None:
        """Plotly Figure'ı geçici HTML dosyasına yazar ve view'a yükler."""
        page = self.page

        try:
            page.shared_plotly_path = ensure_patched_plotly_js()
            shared_js_url = QUrl.fromLocalFile(page.shared_plotly_path).toString()
            html = build_plotly_html(fig, shared_js_url)
        except Exception as exc:
            logger.error("Failed to prepare patched Plotly JS, using inline fallback: %s", exc)
            html = build_plotly_html(fig, None)

        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()

        if not hasattr(page, "_view_temp_files"):
            page._view_temp_files = {}
        old_path = page._view_temp_files.get(view)
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
        page._view_temp_files[view] = tmp.name
        view.load(QUrl.fromLocalFile(tmp.name))
