"""
ComparisonController — Karşılaştırma Laboratuvarı QML controller'ı.

Sorumluluk:
- analysis_service.get_portfolio_options() ve get_benchmark_definitions() ile varlık listesi
- analysis_service.get_comparison_view(filter_state) ile çoklu portföy ve benchmark serisi
- Asenkron ThreadPoolExecutor ile UI bloklamayan akıcı hesaplama
- 3 Karşılaştırma Modu: Normal, Normalize (Baz 100), Rasyo (A / B)
- 4 Grafik Görünümü:
    1. Kümülatif Getiri (Normal / Normalize / Rasyo)
    2. Maksimum Değer Kaybı (Drawdown %)
    3. Aylık Dönemsel Getiriler (Bar Chart)
    4. Risk / Getiri Saçılımı (Scatter Plot)
- Risk-Getiri metrik tablosu (Toplam Getiri %, Yıllık Volatilite %)
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pathlib import Path
from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.analysis.comparison_service import ComparisonService
from src.application.services.analysis.models import AnalysisFilterState
from src.ui.pages.comparison.utils.comparison_series_builder import ComparisonSeriesBuilder

logger = logging.getLogger(__name__)

_JS_DIR = Path(__file__).resolve().parent.parent / "assets" / "js"
_LW_CHARTS_JS: str = ""
_CHART_JS: str = ""


def _load_embedded_scripts() -> None:
    global _LW_CHARTS_JS, _CHART_JS
    if not _LW_CHARTS_JS:
        lw_file = _JS_DIR / "lightweight-charts.standalone.production.js"
        if lw_file.exists():
            try:
                _LW_CHARTS_JS = lw_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("lightweight-charts script okunamadı: %s", e)
    if not _CHART_JS:
        chart_file = _JS_DIR / "chart.umd.min.js"
        if chart_file.exists():
            try:
                _CHART_JS = chart_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("chart.umd.min.js script okunamadı: %s", e)


PALETTE = [
    "#2962ff", "#089981", "#f23645", "#ff9800",
    "#ab47bc", "#00bcd4", "#ff5722", "#4caf50",
    "#e91e63", "#3f51b5", "#009688", "#ffc107"
]


class ComparisonController(QObject):
    """QML context property: comparisonController"""

    # --- Signals ---
    assetOptionsChanged = Signal()
    selectedAssetsChanged = Signal()
    chartHtmlChanged = Signal()
    metricsListChanged = Signal()
    isLoadingChanged = Signal()
    periodLabelChanged = Signal()
    comparisonModeChanged = Signal()
    activeChartTabChanged = Signal()
    ratioAssetsChanged = Signal()
    operationResult = Signal(bool, str, arguments=["success", "message"])

    # Worker Thread Signals (Qt QueuedConnection ile GUI ana thread'ine güvenli iletim)
    _calcFinished = Signal(object, object, object)
    _calcEmpty = Signal()
    _calcError = Signal(str)

    def __init__(self, container, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._analysis_service = container.analysis_service
        self._stock_repo = getattr(container, "stock_repo", None)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ComparisonWorker")

        # Worker sinyal bağlantıları (ana GUI thread'inde çalışır)
        self._calcFinished.connect(self._apply_calculation_result)
        self._calcEmpty.connect(self._apply_empty_result)
        self._calcError.connect(self._apply_error_result)

        # State
        self._asset_options: List[Dict[str, str]] = []
        self._selected_codes: List[str] = ["dashboard", "bist100"]
        self._chart_html: str = ""
        self._metrics_list: List[Dict[str, Any]] = []
        self._is_loading: bool = False
        self._period_label: str = "3A"
        self._comparison_mode: str = "NORMALIZED"  # "NORMALIZED", "NORMAL", "RATIO"
        self._active_chart_tab: int = 0  # 0: Getiri, 1: Drawdown, 2: Aylık, 3: Saçılım
        self._ratio_numerator: str = "dashboard"
        self._ratio_denominator: str = "bist100"

        # Cache of aligned data
        self._cached_aligned: Optional[pd.DataFrame] = None
        self._cached_labels: Dict[str, str] = {}

    # ──────────────────────────── QML Properties ────────────────────────────

    @Property(list, notify=assetOptionsChanged)
    def assetOptions(self) -> list:
        return self._asset_options

    @Property(list, notify=selectedAssetsChanged)
    def selectedAssets(self) -> list:
        return self._selected_codes

    @Property(str, notify=chartHtmlChanged)
    def chartHtml(self) -> str:
        return self._chart_html

    @Property(list, notify=metricsListChanged)
    def metricsList(self) -> list:
        return self._metrics_list

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=periodLabelChanged)
    def periodLabel(self) -> str:
        return self._period_label

    @Property(str, notify=comparisonModeChanged)
    def comparisonMode(self) -> str:
        return self._comparison_mode

    @Property(int, notify=activeChartTabChanged)
    def activeChartTab(self) -> int:
        return self._active_chart_tab

    @Property(str, notify=ratioAssetsChanged)
    def ratioNumerator(self) -> str:
        return self._ratio_numerator

    @Property(str, notify=ratioAssetsChanged)
    def ratioDenominator(self) -> str:
        return self._ratio_denominator

    # ──────────────────────────── QML Slots ────────────────────────────

    @Slot()
    def loadAssetOptions(self) -> None:
        """Portföy ve benchmark seçeneklerini yükler."""
        try:
            options: List[Dict[str, str]] = []

            # 1. Portföyler
            portfolios = self._analysis_service.get_portfolio_options()
            for p in portfolios:
                options.append({"code": p.code, "label": p.label, "kind": p.kind})

            # 2. Benchmarklar
            benchmarks = self._analysis_service.get_benchmark_definitions()
            for b in benchmarks:
                options.append({"code": b.code, "label": b.label, "kind": b.kind})

            self._asset_options = options
            self.assetOptionsChanged.emit()

            valid_codes = {o["code"] for o in options}
            self._selected_codes = [c for c in self._selected_codes if c in valid_codes]
            if not self._selected_codes and options:
                self._selected_codes = [o["code"] for o in options[:2]]

            self.selectedAssetsChanged.emit()
        except Exception as exc:
            logger.exception("Varlık seçenekleri yüklenemedi: %s", exc)

    @Slot(str, bool)
    def toggleAsset(self, code: str, selected: bool) -> None:
        """Bir varlığı seçili listeye ekler veya çıkarır."""
        if selected and code not in self._selected_codes:
            self._selected_codes.append(code)
        elif not selected and code in self._selected_codes:
            self._selected_codes.remove(code)
        self.selectedAssetsChanged.emit()

    @Slot(str)
    def setPeriod(self, label: str) -> None:
        """Dönem butonundan seçim yapar."""
        self._period_label = label
        self.periodLabelChanged.emit()
        self.runComparison()

    @Slot(str)
    def setComparisonMode(self, mode: str) -> None:
        """Karşılaştırma modunu ayarlar: NORMALIZED, NORMAL, RATIO."""
        if mode in ("NORMALIZED", "NORMAL", "RATIO"):
            self._comparison_mode = mode
            self.comparisonModeChanged.emit()
            self._render_current_chart()

    @Slot(int)
    def setActiveChartTab(self, tab_index: int) -> None:
        """Aktif grafik sekmesini ayarlar: 0: Getiri, 1: Drawdown, 2: Aylık, 3: Saçılım."""
        if 0 <= tab_index <= 3:
            self._active_chart_tab = tab_index
            self.activeChartTabChanged.emit()
            self._render_current_chart()

    @Slot(str, str)
    def setRatioAssets(self, num_code: str, den_code: str) -> None:
        """Rasyo modu için pay ve payda varlıklarını ayarlar."""
        self._ratio_numerator = num_code
        self._ratio_denominator = den_code
        self.ratioAssetsChanged.emit()
        if self._comparison_mode == "RATIO":
            self._render_current_chart()

    @Slot()
    def runComparison(self) -> None:
        """Asenkron arka plan iş parçacığında karşılaştırmayı çalıştırır."""
        if not self._selected_codes:
            self._chart_html = ""
            self._metrics_list = []
            self.chartHtmlChanged.emit()
            self.metricsListChanged.emit()
            return

        self._is_loading = True
        self.isLoadingChanged.emit()

        selected_codes = list(self._selected_codes)
        period_label = self._period_label

        self._executor.submit(self._worker_calculate, selected_codes, period_label)

    def _worker_calculate(self, selected_codes: List[str], period_label: str) -> None:
        """Arka plan thread'inde veri çekimi ve hizalama hesabı."""
        try:
            end_dt = date.today()
            start_dt = self._resolve_start_date(period_label, end_dt)

            portfolio_sources: List[str] = []
            benchmarks: List[str] = []

            for code in selected_codes:
                if code == "dashboard" or code.startswith("model:") or code.startswith("portfolio:"):
                    portfolio_sources.append(code)
                else:
                    benchmarks.append(code)

            primary_source = portfolio_sources[0] if portfolio_sources else "dashboard"

            filter_state = AnalysisFilterState(
                start_date=start_dt,
                end_date=end_dt,
                selected_stock_ids=[],
                selected_benchmarks=benchmarks,
                portfolio_source=primary_source,
                comparison_portfolio_sources=portfolio_sources,
                currency_mode="TL",
            )

            dto = self._analysis_service.get_comparison_view(filter_state)
            series_dict, code_to_label = ComparisonSeriesBuilder.build_global_series(dto, [])

            if not series_dict:
                self._calcEmpty.emit()
                return

            aligned = ComparisonService.align_financial_series(series_dict)
            if aligned.empty or len(aligned) < 2:
                self._calcEmpty.emit()
                return

            # Risk-Getiri Metrikleri
            risk_return = ComparisonService.calculate_risk_return_metrics(aligned)
            metrics = []
            for col in aligned.columns:
                rm = risk_return.get(col, {})
                metrics.append({
                    "code": col,
                    "label": col,
                    "totalReturn": round(rm.get("total_return_pct", 0.0), 2),
                    "volatility": round(rm.get("annual_volatility_pct", 0.0), 2),
                })

            # Ana GUI thread'ine Qt QueuedConnection ile aktar
            self._calcFinished.emit(aligned, code_to_label, metrics)
        except Exception as exc:
            logger.exception("Arka plan karşılaştırma hatası: %s", exc)
            self._calcError.emit(str(exc))

    def _apply_empty_result(self) -> None:
        self._cached_aligned = None
        self._chart_html = ""
        self._metrics_list = []
        self._is_loading = False
        self.isLoadingChanged.emit()
        self.chartHtmlChanged.emit()
        self.metricsListChanged.emit()

    def _apply_error_result(self, err_msg: str) -> None:
        self._is_loading = False
        self.isLoadingChanged.emit()
        self.operationResult.emit(False, err_msg)

    def _apply_calculation_result(self, aligned: pd.DataFrame, code_to_label: Dict[str, str], metrics: List[Dict[str, Any]]) -> None:
        self._cached_aligned = aligned
        self._cached_labels = code_to_label
        self._metrics_list = metrics
        self._metrics_list_changed = True
        self.metricsListChanged.emit()
        self._is_loading = False
        self.isLoadingChanged.emit()
        self._render_current_chart()

    def _render_current_chart(self) -> None:
        """Mevcut sekme ve moda göre aktif grafiğin HTML'ini üretir."""
        aligned = self._cached_aligned
        if aligned is None or aligned.empty:
            self._chart_html = ""
            self.chartHtmlChanged.emit()
            return

        if self._active_chart_tab == 0:
            # Sekme 0: Kümülatif Getiri
            if self._comparison_mode == "RATIO":
                num_col = self._find_column(aligned, self._ratio_numerator)
                den_col = self._find_column(aligned, self._ratio_denominator)
                if num_col and den_col and num_col in aligned and den_col in aligned:
                    ratio_series = ComparisonService.calculate_asset_ratio(aligned[num_col], aligned[den_col])
                    ratio_df = pd.DataFrame({f"{num_col} / {den_col}": ratio_series})
                    self._chart_html = self._build_line_chart_html(ratio_df, is_ratio=True)
                else:
                    self._chart_html = self._build_line_chart_html(aligned, is_ratio=False)
            elif self._comparison_mode == "NORMAL":
                self._chart_html = self._build_line_chart_html(aligned, is_normal=True)
            else:
                # NORMALIZED (Baz 100)
                first_row = aligned.iloc[0]
                norm = (aligned.divide(first_row)) * 100.0
                norm = norm.replace([float('inf'), float('-inf')], float('nan')).ffill().bfill()
                self._chart_html = self._build_line_chart_html(norm, is_normalized=True)

        elif self._active_chart_tab == 1:
            # Sekme 1: Maksimum Değer Kaybı (Drawdown)
            dd = ComparisonService.calculate_drawdowns(aligned)
            self._chart_html = self._build_drawdown_html(dd)

        elif self._active_chart_tab == 2:
            # Sekme 2: Aylık Dönemsel Getiriler
            monthly = ComparisonService.calculate_periodic_returns(aligned, freq="ME")
            self._chart_html = self._build_periodic_html(monthly)

        elif self._active_chart_tab == 3:
            # Sekme 3: Risk-Getiri Saçılımı (Scatter Plot)
            self._chart_html = self._build_scatter_html(self._metrics_list)

        self.chartHtmlChanged.emit()

    def _find_column(self, df: pd.DataFrame, code: str) -> Optional[str]:
        if code in df.columns:
            return code
        for c in df.columns:
            if code.lower() in c.lower() or c.lower() in code.lower():
                return c
        return df.columns[0] if len(df.columns) > 0 else None

    # ──────────────────────────── HTML Builders ────────────────────────────

    def _resolve_start_date(self, label: str, end_dt: date) -> date:
        mapping = {
            "1A": timedelta(days=30),
            "3A": timedelta(days=90),
            "6A": timedelta(days=180),
            "1Y": timedelta(days=365),
        }
        if label in mapping:
            return end_dt - mapping[label]
        if label == "YBB":
            return date(end_dt.year, 1, 1)
        return date(2022, 1, 1)

    def _build_line_chart_html(self, df: pd.DataFrame, is_ratio: bool = False, is_normal: bool = False, is_normalized: bool = False) -> str:
        datasets_js = []
        for i, col in enumerate(df.columns):
            color = PALETTE[i % len(PALETTE)]
            series = df[col].dropna()
            data_points = []
            for dt_val, val in series.items():
                time_str = dt_val.strftime("%Y-%m-%d") if hasattr(dt_val, "strftime") else str(dt_val)[:10]
                data_points.append(f"{{time:'{time_str}',value:{float(val):.2f}}}")

            datasets_js.append(f"""
                var s{i} = chart.addSeries(LightweightCharts.LineSeries, {{
                    color: '{color}',
                    lineWidth: 2,
                    title: '{col}'
                }});
                s{i}.setData([{','.join(data_points)}]);
            """)

        title_note = "Rasyo (A/B)" if is_ratio else ("Fiyat / Değer" if is_normal else "Normalize Getiri (Baz 100)")
        return self._wrap_lw_chart(''.join(datasets_js), title_note)

    def _build_drawdown_html(self, dd_df: pd.DataFrame) -> str:
        """Drawdown derinlik eğrileri (negatif yüzdeler)."""
        datasets_js = []
        for i, col in enumerate(dd_df.columns):
            color = PALETTE[i % len(PALETTE)]
            series = dd_df[col].dropna()
            data_points = []
            for dt_val, val in series.items():
                time_str = dt_val.strftime("%Y-%m-%d") if hasattr(dt_val, "strftime") else str(dt_val)[:10]
                data_points.append(f"{{time:'{time_str}',value:{float(val):.2f}}}")

            datasets_js.append(f"""
                var s{i} = chart.addSeries(LightweightCharts.AreaSeries, {{
                    topColor: 'rgba(0, 0, 0, 0)',
                    bottomColor: '{color}22',
                    lineColor: '{color}',
                    lineWidth: 2,
                    title: '{col}'
                }});
                s{i}.setData([{','.join(data_points)}]);
            """)

        return self._wrap_lw_chart(''.join(datasets_js), "Maksimum Değer Kaybı (Drawdown %)")

    def _wrap_lw_chart(self, series_code: str, title: str) -> str:
        _load_embedded_scripts()
        script_tag = f"<script>{_LW_CHARTS_JS}</script>" if _LW_CHARTS_JS else '<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>'
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body {{ margin: 0; background: #131722; overflow: hidden; }} #c {{ width: 100vw; height: 100vh; }}</style>
{script_tag}
</head><body><div id="c"></div>
<script>
var chart = LightweightCharts.createChart(document.getElementById('c'), {{
    width: window.innerWidth || 800, height: window.innerHeight || 450,
    layout: {{ background: {{ color: '#131722' }}, textColor: '#9db2ce' }},
    grid: {{ vertLines: {{ color: '#1e222d' }}, horzLines: {{ color: '#1e222d' }} }},
    rightPriceScale: {{ borderColor: '#2a2e39', scaleMargins: {{ top: 0.1, bottom: 0.1 }} }},
    timeScale: {{ borderColor: '#2a2e39', timeVisible: false }},
    crosshair: {{ mode: 0 }}
}});
{series_code}
chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
    chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
}});
</script></body></html>"""

    def _build_periodic_html(self, monthly_df: pd.DataFrame) -> str:
        """Aylık getirileri yan yana gösteren interaktif Chart.js Bar Grafiği."""
        _load_embedded_scripts()
        script_tag = f"<script>{_CHART_JS}</script>" if _CHART_JS else '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
        labels = [d.strftime("%Y-%m") if hasattr(d, "strftime") else str(d)[:7] for d in monthly_df.index]
        datasets = []
        for i, col in enumerate(monthly_df.columns):
            color = PALETTE[i % len(PALETTE)]
            vals = [round(float(v), 2) if not pd.isna(v) else 0 for v in monthly_df[col]]
            datasets.append(f"""{{
                label: '{col}',
                data: {vals},
                backgroundColor: '{color}cc',
                borderColor: '{color}',
                borderWidth: 1
            }}""")

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
{script_tag}
<style>body{{margin:12px;background:#131722;color:#9db2ce;overflow:hidden}}#chart-wrap{{width:98vw;height:90vh}}</style>
</head><body><div id="chart-wrap"><canvas id="pChart"></canvas></div>
<script>
new Chart(document.getElementById('pChart'), {{
    type: 'bar',
    data: {{
        labels: {labels},
        datasets: [{','.join(datasets)}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ labels: {{ color: '#9db2ce', font: {{ family: 'Segoe UI' }} }} }}
        }},
        scales: {{
            x: {{ grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce' }} }},
            y: {{ grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce', callback: v => '%' + v }} }}
        }}
    }}
}});
</script></body></html>"""

    def _build_scatter_html(self, metrics: List[Dict[str, Any]]) -> str:
        """Risk / Getiri Saçılım (Scatter Plot) Grafiği."""
        _load_embedded_scripts()
        script_tag = f"<script>{_CHART_JS}</script>" if _CHART_JS else '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
        datasets = []
        for i, m in enumerate(metrics):
            color = PALETTE[i % len(PALETTE)]
            datasets.append(f"""{{
                label: '{m["label"]}',
                data: [{{ x: {m["volatility"]}, y: {m["totalReturn"]} }}],
                backgroundColor: '{color}',
                borderColor: '#ffffff',
                borderWidth: 2,
                pointRadius: 9,
                pointHoverRadius: 12
            }}""")

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
{script_tag}
<style>body{{margin:12px;background:#131722;color:#9db2ce;overflow:hidden}}#chart-wrap{{width:98vw;height:90vh}}</style>
</head><body><div id="chart-wrap"><canvas id="sChart"></canvas></div>
<script>
new Chart(document.getElementById('sChart'), {{
    type: 'scatter',
    data: {{
        datasets: [{','.join(datasets)}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ labels: {{ color: '#9db2ce', font: {{ family: 'Segoe UI' }} }} }},
            tooltip: {{
                callbacks: {{
                    label: function(ctx) {{
                        return ctx.dataset.label + ' -> Risk: %' + ctx.raw.x + ' | Getiri: %' + ctx.raw.y;
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                title: {{ display: true, text: 'Yıllık Volatilite (Oynaklık / Risk %)', color: '#9db2ce' }},
                grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce' }}
            }},
            y: {{
                title: {{ display: true, text: 'Toplam Getiri (%)', color: '#9db2ce' }},
                grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce' }}
            }}
        }}
    }}
}});
</script></body></html>"""
