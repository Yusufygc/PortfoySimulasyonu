# src/ui/pages/comparison/utils/chart_renderer.py
"""Karşılaştırma sayfasındaki tüm grafik ve tablo render işlemleri."""
from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
import os
import re
import tempfile
import unicodedata
from typing import TYPE_CHECKING, NamedTuple

import pandas as pd
import plotly.graph_objects as go
from src.qt_compat.qtcore import Qt, QUrl, QThreadPool, QTimer
from src.qt_compat.qtgui import QBrush, QColor
from src.qt_compat.lifecycle import is_qobject_deleted as _is_qobject_deleted
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
from src.qt_compat.qtwidgets import QTableWidgetItem

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

_DOWNLOAD_CHART_LABELS = {
    "main": "ana_performans",
    "drawdown": "drawdown",
    "periodic": "donemsel_getiri",
    "scatter": "risk_getiri",
    "treemap": "treemap",
}

_CHART_NAMES = ("main", "drawdown", "periodic", "scatter", "treemap")


def _find_column(df: pd.DataFrame, code: str, code_to_label: dict) -> str | None:
    label = code_to_label.get(code)
    if label and label in df.columns:
        return label
    for col in df.columns:
        if col.lower() == code.lower() or (code.isdigit() and col == code):
            return col
        if code.lower().replace(" ", "").replace("_", "") in col.lower().replace(" ", "").replace("_", ""):
            return col
    return df.columns[0] if not df.empty else None


def _fallback_cumulative(df: pd.DataFrame, fig: go.Figure) -> None:
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
            line=dict(width=2, color=_COLORS[i % len(_COLORS)]),
            hovertemplate=ComparisonChartFactory._date_value_hover_template()
        ))
    ComparisonChartFactory._apply_theme_layout(fig, L10N.KUMULATIF_PERFORMANS_GETIRISI)


def build_main_fig(df: pd.DataFrame, mode: str, ratio_assets: tuple | None, code_to_label: dict) -> go.Figure:
    fig = go.Figure()

    if mode == L10N.NORMALIZE_BAZ_100:
        df_norm = df.copy()
        for col in df_norm.columns:
            base_val = df_norm[col].iloc[0]
            if base_val != 0:
                df_norm[col] = (df_norm[col] / base_val) * 100.0
        for i, col in enumerate(df_norm.columns):
            fig.add_trace(go.Scatter(
                x=df_norm.index, y=df_norm[col], name=col,
                line=dict(width=2, color=_COLORS[i % len(_COLORS)]),
                hovertemplate=ComparisonChartFactory._date_value_hover_template()
            ))
        ComparisonChartFactory._apply_theme_layout(fig, L10N.NORMALIZE_PERFORMANS_KIYASLAMASI_BAZ_100)
    elif mode == L10N.RASYO_MODU and ratio_assets:
        num_col = _find_column(df, ratio_assets[0], code_to_label)
        den_col = _find_column(df, ratio_assets[1], code_to_label)
        if num_col and den_col:
            ratio_series = ComparisonService.calculate_asset_ratio(df[num_col], df[den_col])
            ratio_name = f"{num_col} / {den_col}"
            fig.add_trace(go.Scatter(
                x=ratio_series.index, y=ratio_series.values,
                name=ratio_name,
                line=dict(width=2, color="#00D4FF"),
                hovertemplate=ComparisonChartFactory._date_value_hover_template()
            ))
            ComparisonChartFactory._apply_theme_layout(fig, f"Rasyo GÃ¶sterimi: {ratio_name}")
        else:
            _fallback_cumulative(df, fig)
    else:
        _fallback_cumulative(df, fig)

    ComparisonChartFactory._apply_date_axis_format(fig)
    return fig


class _FigCtx(NamedTuple):
    mode: str
    ratio_assets: tuple | None
    code_to_label: dict


class _DownloadCtx(NamedTuple):
    selected_assets: "list[str]"
    ratio_assets: "tuple[str, str] | None"
    code_to_label: "dict[str, str]"
    asset_labels: "dict[str, str]"


def _resolve_asset_label(code: str, code_to_label: dict[str, str], asset_labels: dict[str, str]) -> str:
    return code_to_label.get(code) or asset_labels.get(code) or code


def _codes_for_mode(mode: str, selected_assets: list, ratio_assets: tuple | None) -> list:
    if mode == L10N.RASYO_MODU and ratio_assets:
        return [code for code in ratio_assets if code]
    return [code for code in selected_assets if code]


def _slugs_from_codes(codes: list, code_to_label: dict, asset_labels: dict) -> list:
    labels = [_resolve_asset_label(code, code_to_label, asset_labels) for code in codes if code]
    raw_slugs = [_slugify(label) for label in labels if label]
    return [slug for slug in raw_slugs if slug]


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.lower()).strip("_")
    return re.sub(r"_+", "_", cleaned)


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
        if not self._page_is_available():
            return
        if df.empty:
            return
            
        page = self.page
        mode = page.ribbon_bar.selected_mode()
        df_metrics = df if mode == L10N.RASYO_MODU else df
        
        # Summary table anında render edilebilir (hafif)
        if not page.chart_overrides.get("summary_table"):
            self.render_summary_table(df_metrics)
            
        # Mevcut olan WebEngineView'lar için asenkron render başlat
        for name in _CHART_NAMES:
            view = getattr(page, f"_{name}_chart_view", None)
            if view is not None and not _is_qobject_deleted(view):
                if not page.chart_overrides.get(f"{name}_chart"):
                    self.render_single_chart_async(name, df)
        
        # Görünürlük kontrolünü çalıştır (belki henüz yaratılmamış ama ekranda olan vardır)
        if hasattr(page, "_view_manager"):
            page._view_manager.check_viewport_visibility()

    def render_single_chart_async(self, chart_key: str, df: pd.DataFrame) -> None:
        """Tek bir grafiği worker üzerinden asenkron oluşturur."""
        if df.empty:
            return
            
        if not self._page_is_available():
            return

        mapped_key = _KEY_MAP.get(chart_key, chart_key)
            
        page = self.page
        mode = page.ribbon_bar.selected_mode()
        selected_assets = page.ribbon_bar.selected_assets()
        start_date, end_date = page.ribbon_bar.date_range()
        ratio_assets = page.ribbon_bar.ratio_assets() if mode == L10N.RASYO_MODU else None
        code_to_label = getattr(page, "code_to_label", {}).copy()
        asset_labels = getattr(page, "_asset_labels", {}).copy()
        download_filename = self._build_download_filename(
            chart_key=mapped_key,
            mode=mode,
            start_date=start_date,
            end_date=end_date,
            ctx=_DownloadCtx(selected_assets, ratio_assets, code_to_label, asset_labels),
        )
        
        worker = Worker(
            self._generate_html_in_background,
            mapped_key, df.copy(), _FigCtx(mode, ratio_assets, code_to_label), download_filename
        )
        worker.signals.result.connect(self._on_html_ready)
        worker.signals.error.connect(lambda err: logger.error(f"Render error for {mapped_key}: {err}"))
        self.threadpool.start(worker)

    def _build_fig_for_key(self, chart_key: str, df: pd.DataFrame, ctx: "_FigCtx"):
        df_metrics = df
        if chart_key == "main":
            return self._build_main_fig(df, ctx.mode, ctx.ratio_assets, ctx.code_to_label)
        elif chart_key == "drawdown":
            return ComparisonChartFactory.build_drawdown_chart(ComparisonService.calculate_drawdowns(df_metrics))
        elif chart_key == "periodic":
            return ComparisonChartFactory.build_period_bar_chart(
                ComparisonService.calculate_periodic_returns(df_metrics, freq="ME")
            )
        elif chart_key == "scatter":
            metrics = ComparisonService.calculate_risk_return_metrics(df_metrics)
            scatter_data = [
                {L10N.VOLATILITE: m["annual_volatility_pct"], L10N.GETIRI: m["total_return_pct"], "Varlık": name}
                for name, m in metrics.items()
            ]
            return ComparisonChartFactory.build_risk_return_scatter(pd.DataFrame(scatter_data).set_index("Varlık"))
        elif chart_key == "treemap":
            metrics = ComparisonService.calculate_risk_return_metrics(df_metrics)
            weights = [max(abs(m["total_return_pct"]), 1.0) for m in metrics.values()]
            df_weights = pd.DataFrame(
                {L10N.VARLIK_AGIRLIGI: weights, L10N.GETIRI: [m["total_return_pct"] for m in metrics.values()]},
                index=df.columns,
            )
            return ComparisonChartFactory.build_treemap(df_weights)
        return None

    def _generate_html_in_background(
        self,
        chart_key: str,
        df: pd.DataFrame,
        ctx: "_FigCtx",
        download_filename: str,
    ) -> tuple[str, str] | None:
        fig = self._build_fig_for_key(chart_key, df, ctx)
        if not fig:
            return None

        try:
            shared_plotly_path = ensure_patched_plotly_js()
            shared_js_url = QUrl.fromLocalFile(shared_plotly_path).toString()
            html = build_plotly_html(fig, shared_js_url, download_filename)
        except Exception as exc:
            logger.error("Failed to prepare patched Plotly JS: %s", exc)
            html = build_plotly_html(fig, None, download_filename)

        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        tmp.write(html)
        tmp.close()

        return chart_key, tmp.name

    def _on_html_ready(self, result: tuple[str, str] | None) -> None:
        """Worker bittiğinde ana thread üzerinden Chromium'u besler (Kuyruk ile)."""
        if not self._page_is_available():
            if result:
                self._remove_temp_file(result[1])
            return
        if not result:
            return
        chart_key, temp_file_path = result
        view_attr = f"_{chart_key}_chart_view"
        view = getattr(self.page, view_attr, None)
        if not view or _is_qobject_deleted(view):
            self._remove_temp_file(temp_file_path)
            return

        self._load_queue.append((view, temp_file_path))
        if not self._load_timer.isActive():
            self._load_timer.start(50)

    def _process_load_queue(self) -> None:
        """Sıradaki WebEngineView'a HTML dosyasını yükler."""
        if not self._page_is_available():
            self._clear_load_queue()
            return
        if not self._load_queue:
            return
            
        view, temp_file_path = self._load_queue.pop(0)
        if _is_qobject_deleted(view):
            self._remove_temp_file(temp_file_path)
            if self._load_queue:
                self._load_timer.start(250)
            return
        
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
        return build_main_fig(df, mode, ratio_assets, code_to_label)

    def _build_download_filename(
        self,
        chart_key: str,
        mode: str,
        start_date,
        end_date,
        ctx: _DownloadCtx,
    ) -> str:
        asset_part = self._build_asset_filename_part(
            selected_assets=ctx.selected_assets,
            mode=mode,
            ratio_assets=ctx.ratio_assets,
            code_to_label=ctx.code_to_label,
            asset_labels=ctx.asset_labels,
        )
        chart_part = _DOWNLOAD_CHART_LABELS.get(chart_key, _slugify(chart_key))
        mode_part = _slugify(mode)
        start_part = start_date.strftime("%d.%m.%Y")
        end_part = end_date.strftime("%d.%m.%Y")
        return f"{asset_part}_{chart_part}_{mode_part}_{start_part}_{end_part}"

    def _build_asset_filename_part(
        self,
        selected_assets: list[str],
        mode: str,
        ratio_assets: tuple[str, str] | None,
        code_to_label: dict[str, str],
        asset_labels: dict[str, str],
    ) -> str:
        codes = _codes_for_mode(mode, selected_assets, ratio_assets)
        slugs = _slugs_from_codes(codes, code_to_label, asset_labels)
        return "_".join(slugs) if slugs else "varlik"

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
        page._comparison_empty_message = message
        page.last_global_df = None
        empty_html = _EMPTY_HTML.format(message=message)
        page.summary_table.setRowCount(0)
        
        for name in _CHART_NAMES:
            view = getattr(page, f"_{name}_chart_view", None)
            if view and not _is_qobject_deleted(view):
                view.setHtml(empty_html)
                continue
            placeholder = getattr(page, f"{name}_chart_placeholder", None)
            if placeholder and not _is_qobject_deleted(placeholder):
                placeholder.label.setText(message)

    def _load_plotly_to_view(self, view: SilentWebEngineView, fig: go.Figure) -> None:
        """Plotly Figure'ı geçici HTML dosyasına yazar ve view'a yükler."""
        if not self._page_is_available() or _is_qobject_deleted(view):
            return
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

    def cleanup(self) -> None:
        """Cancel pending WebEngine load jobs before page teardown."""
        if self._load_timer.isActive():
            self._load_timer.stop()
        self._clear_load_queue()

    def _clear_load_queue(self) -> None:
        while self._load_queue:
            _, temp_file_path = self._load_queue.pop(0)
            self._remove_temp_file(temp_file_path)

    @staticmethod
    def _remove_temp_file(path: str) -> None:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def _page_is_available(self) -> bool:
        page = self.page
        if getattr(page, "_comparison_page_active", True) is False:
            return False
        return not _is_qobject_deleted(page)

