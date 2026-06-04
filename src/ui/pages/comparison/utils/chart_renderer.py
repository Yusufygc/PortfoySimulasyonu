# src/ui/pages/comparison/utils/chart_renderer.py
"""Karşılaştırma sayfasındaki tüm grafik ve tablo render işlemleri."""
from __future__ import annotations

import logging
import os
import tempfile
from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objects as go
from PyQt5.QtCore import Qt, QUrl, QThreadPool, QTimer
from PyQt5.QtGui import QBrush, QColor
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
from PyQt5.QtWidgets import QTableWidgetItem

from src.application.services.analysis.comparison_service import ComparisonService
from src.ui.pages.comparison.chart_factory import ComparisonChartFactory
from src.ui.pages.comparison.utils.plotly_html import build_plotly_html, ensure_patched_plotly_js
from src.ui.worker import Worker

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

_KEY_MAP = {
    "main_chart": "main",
    "drawdown_chart": "drawdown",
    "periodic_chart": "periodic",
    "scatter_chart": "scatter",
    "treemap_chart": "treemap",
    "main": "main",
    "drawdown": "drawdown",
    "periodic": "periodic",
    "scatter": "scatter",
    "treemap": "treemap"
}

class ChartRenderer:
    """Plotly grafiklerini, QTableWidget içeriğini ve boş durumu yönetir."""

    def __init__(self, page: ComparisonPage) -> None:
        self.page = page
        self.threadpool = QThreadPool.globalInstance()
        self._load_queue: list[tuple[SilentWebEngineView, str]] = []
        self._load_timer = QTimer()
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._process_load_queue)

    # ------------------------------------------------------------------
    # Asenkron Toplu Render
    # ------------------------------------------------------------------

    def trigger_visible_charts_render(self, df: pd.DataFrame) -> None:
        """Veri değiştiğinde halihazırda oluşturulmuş tüm WebEngineView'ları günceller."""
        if df.empty:
            return
            
        page = self.page
        mode = page.ribbon_bar.selected_mode()
        df_metrics = df if mode == "Rasyo Modu" else df
        
        # Summary table anında render edilebilir (hafif)
        if not page.chart_overrides.get("summary_table"):
            self.render_summary_table(df_metrics)
            
        # Mevcut olan WebEngineView'lar için asenkron render başlat
        for name in ["main", "drawdown", "periodic", "scatter", "treemap"]:
            if getattr(page, f"_{name}_chart_view", None) is not None:
                if not page.chart_overrides.get(f"{name}_chart"):
                    self.render_single_chart_async(name, df)
        
        # Görünürlük kontrolünü çalıştır (belki henüz yaratılmamış ama ekranda olan vardır)
        if hasattr(page, "_view_manager"):
            page._view_manager.check_viewport_visibility()

    def render_single_chart_async(self, chart_key: str, df: pd.DataFrame) -> None:
        """Tek bir grafiği worker üzerinden asenkron oluşturur."""
        if df.empty:
            return
            
        mapped_key = _KEY_MAP.get(chart_key, chart_key)
            
        page = self.page
        mode = page.ribbon_bar.selected_mode()
        ratio_assets = page.ribbon_bar.ratio_assets() if mode == "Rasyo Modu" else None
        code_to_label = getattr(page, "code_to_label", {}).copy()
        
        worker = Worker(
            self._generate_html_in_background, 
            mapped_key, df.copy(), mode, ratio_assets, code_to_label
        )
        worker.signals.result.connect(self._on_html_ready)
        worker.signals.error.connect(lambda err: logger.error(f"Render error for {mapped_key}: {err}"))
        self.threadpool.start(worker)

    def _generate_html_in_background(self, chart_key: str, df: pd.DataFrame, mode: str, ratio_assets: tuple | None, code_to_label: dict) -> tuple[str, str] | None:
        """Arka planda çalışacak fonksiyon."""
        df_metrics = df if mode == "Rasyo Modu" else df
        fig = None

        if chart_key == "main":
            fig = self._build_main_fig(df, mode, ratio_assets, code_to_label)
        elif chart_key == "drawdown":
            df_dd = ComparisonService.calculate_drawdowns(df_metrics)
            fig = ComparisonChartFactory.build_drawdown_chart(df_dd)
        elif chart_key == "periodic":
            df_periodic = ComparisonService.calculate_periodic_returns(df_metrics, freq="ME")
            fig = ComparisonChartFactory.build_period_bar_chart(df_periodic)
        elif chart_key == "scatter":
            metrics = ComparisonService.calculate_risk_return_metrics(df_metrics)
            scatter_data = [
                {"Volatilite %": m["annual_volatility_pct"], "Getiri %": m["total_return_pct"], "Varlık": name}
                for name, m in metrics.items()
            ]
            df_scatter = pd.DataFrame(scatter_data).set_index("Varlık")
            fig = ComparisonChartFactory.build_risk_return_scatter(df_scatter)
        elif chart_key == "treemap":
            metrics = ComparisonService.calculate_risk_return_metrics(df_metrics)
            weights = [max(abs(m["total_return_pct"]), 1.0) for m in metrics.values()]
            df_weights = pd.DataFrame(
                {"Varlık Ağırlığı %": weights, "Getiri %": [m["total_return_pct"] for m in metrics.values()]},
                index=df.columns,
            )
            fig = ComparisonChartFactory.build_treemap(df_weights)

        if not fig:
            return None

        # Build HTML
        try:
            shared_plotly_path = ensure_patched_plotly_js()
            shared_js_url = QUrl.fromLocalFile(shared_plotly_path).toString()
            html = build_plotly_html(fig, shared_js_url)
        except Exception as exc:
            logger.error("Failed to prepare patched Plotly JS: %s", exc)
            html = build_plotly_html(fig, None)

        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()

        return chart_key, tmp.name

    def _on_html_ready(self, result: tuple[str, str] | None) -> None:
        """Worker bittiğinde ana thread üzerinden Chromium'u besler (Kuyruk ile)."""
        if not result:
            return
        chart_key, temp_file_path = result
        view_attr = f"_{chart_key}_chart_view"
        view = getattr(self.page, view_attr, None)
        if not view:
            return

        self._load_queue.append((view, temp_file_path))
        if not self._load_timer.isActive():
            self._load_timer.start(50)

    def _process_load_queue(self) -> None:
        """Sıradaki WebEngineView'a HTML dosyasını yükler."""
        if not self._load_queue:
            return
            
        view, temp_file_path = self._load_queue.pop(0)
        
        if not hasattr(self.page, "_view_temp_files"):
            self.page._view_temp_files = {}
        old_path = self.page._view_temp_files.get(view)
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
        self.page._view_temp_files[view] = temp_file_path
        
        view.load(QUrl.fromLocalFile(temp_file_path))
        
        if self._load_queue:
            self._load_timer.start(250)  # Chromium yüklemeleri arasına 250ms es ver

    # ------------------------------------------------------------------
    # Geriye dönük uyumluluk (Eski senkron metodlar, override için)
    # ------------------------------------------------------------------

    def render_charts(self, df: pd.DataFrame) -> None:
        """Eski senkron metod. Artık asenkron yapıya yönlendiriyoruz."""
        self.trigger_visible_charts_render(df)

    def render_single_chart(self, chart_key: str, df: pd.DataFrame) -> None:
        """Eski senkron metod. Override vs için asenkron yapıya yönlendirir."""
        if chart_key == "summary_table":
            self.render_summary_table(df)
        else:
            self.render_single_chart_async(chart_key, df)

    # ------------------------------------------------------------------
    # Ana performans grafiği (Worker içi kullanım)
    # ------------------------------------------------------------------

    def _build_main_fig(self, df: pd.DataFrame, mode: str, ratio_assets: tuple | None, code_to_label: dict) -> go.Figure:
        fig = go.Figure()
        
        def find_col(code):
            label = code_to_label.get(code)
            if label and label in df.columns:
                return label
            for col in df.columns:
                if col.lower() == code.lower() or (code.isdigit() and col == code):
                    return col
                if code.lower().replace(" ", "").replace("_", "") in col.lower().replace(" ", "").replace("_", ""):
                    return col
            return df.columns[0] if not df.empty else None

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
            if ratio_assets:
                num_code, den_code = ratio_assets
                num_col = find_col(num_code)
                den_col = find_col(den_code)
                if num_col and den_col:
                    ratio_series = ComparisonService.calculate_asset_ratio(df[num_col], df[den_col])
                    ratio_name = f"{num_col} / {den_col}"
                    fig.add_trace(go.Scatter(
                        x=ratio_series.index, y=ratio_series.values,
                        name=ratio_name, line=dict(width=2, color="#00D4FF")
                    ))
                    ComparisonChartFactory._apply_theme_layout(fig, f"Rasyo Gösterimi: {ratio_name}")
                else:
                    self._fallback_cumulative(df, fig)
            else:
                self._fallback_cumulative(df, fig)
        else:
            self._fallback_cumulative(df, fig)
            
        return fig
        
    def _fallback_cumulative(self, df: pd.DataFrame, fig: go.Figure) -> None:
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

    # ------------------------------------------------------------------
    # Özet tablo (Senkron, hızlı olduğu için UI thread'de kalabilir)
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
    # Boş durum
    # ------------------------------------------------------------------

    def render_empty_state(self, message: str) -> None:
        page = self.page
        empty_html = _EMPTY_HTML.format(message=message)
        if getattr(page, "_main_chart_view", None):
            page.main_chart_view.setHtml(empty_html)
        page.summary_table.setRowCount(0)
        
        for name in ["drawdown", "periodic", "scatter", "treemap"]:
            view = getattr(page, f"_{name}_chart_view", None)
            if view:
                view.setHtml(empty_html)

    def _load_plotly_to_view(self, view: SilentWebEngineView, fig: go.Figure) -> None:
        """Plotly Figure'ı geçici HTML dosyasına yazar ve view'a yükler."""
        page = self.page

        try:
            shared_plotly_path = ensure_patched_plotly_js()
            shared_js_url = QUrl.fromLocalFile(shared_plotly_path).toString()
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

