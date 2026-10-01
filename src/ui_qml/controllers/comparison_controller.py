"""
ComparisonController — Karşılaştırma Laboratuvarı QML controller'ı.

Sorumluluk:
- analysis_service.get_portfolio_options() ve get_benchmark_definitions() ile varlık listesi
- analysis_service.get_comparison_view(filter_state) ile çoklu portföy ve benchmark serisi
- ComparisonSeriesBuilder ve ComparisonService ile serileri birleştirme ve normalize etme (Baz 100)
- Risk-Getiri metriklerini hesaplama (Dönem Getirisi %, Yıllık Volatilite %)
- LightweightCharts interaktif çizgi grafik HTML çıktısı
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from src.application.services.analysis.comparison_service import ComparisonService
from src.application.services.analysis.models import AnalysisFilterState
from src.ui.pages.comparison.utils.comparison_series_builder import ComparisonSeriesBuilder

logger = logging.getLogger(__name__)

BENCHMARK_CODES = {"bist100", "gold", "silver", "usd", "euro", "deposit", "cpi", "xu100"}


class ComparisonController(QObject):
    """QML context property: comparisonController"""

    # --- Signals ---
    assetOptionsChanged = Signal()
    selectedAssetsChanged = Signal()
    chartHtmlChanged = Signal()
    metricsListChanged = Signal()
    isLoadingChanged = Signal()
    periodLabelChanged = Signal()
    operationResult = Signal(bool, str, arguments=["success", "message"])

    def __init__(self, container, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._analysis_service = container.analysis_service
        self._stock_repo = getattr(container, "stock_repo", None)

        # State
        self._asset_options: List[Dict[str, str]] = []
        self._selected_codes: List[str] = ["dashboard", "bist100"]
        self._chart_html: str = ""
        self._metrics_list: List[Dict[str, Any]] = []
        self._is_loading: bool = False
        self._period_label: str = "3A"

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

    # ──────────────────────────── QML Slots ────────────────────────────

    @Slot()
    def loadAssetOptions(self) -> None:
        """Karşılaştırılabilir portföy ve benchmark seçeneklerini yükler."""
        try:
            options: List[Dict[str, str]] = []

            # 1. Portföyler (Ana Portföy ve Model Portföyler)
            portfolios = self._analysis_service.get_portfolio_options()
            for p in portfolios:
                options.append({"code": p.code, "label": p.label, "kind": p.kind})

            # 2. Piyasa Benchmarkları (BIST 100, Altın, Dolar vb.)
            benchmarks = self._analysis_service.get_benchmark_definitions()
            for b in benchmarks:
                options.append({"code": b.code, "label": b.label, "kind": b.kind})

            self._asset_options = options
            self.assetOptionsChanged.emit()

            # Seçili kodların geçerliliğini koru
            valid_codes = {o["code"] for o in options}
            self._selected_codes = [c for c in self._selected_codes if c in valid_codes]
            if not self._selected_codes and options:
                # Varsayılan: Ana portföy ve BIST 100
                first_two = [o["code"] for o in options[:2]]
                self._selected_codes = first_two

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
        """Hızlı dönem butonlarından seçim yapar ve karşılaştırmayı günceller."""
        self._period_label = label
        self.periodLabelChanged.emit()
        self.runComparison()

    @Slot()
    def runComparison(self) -> None:
        """Seçili varlıklarla backend üzerinden karşılaştırma hesaplamasını çalıştırır."""
        if not self._selected_codes:
            self._chart_html = ""
            self._metrics_list = []
            self.chartHtmlChanged.emit()
            self.metricsListChanged.emit()
            return

        self._is_loading = True
        self.isLoadingChanged.emit()

        try:
            end_dt = date.today()
            start_dt = self._resolve_start_date(self._period_label, end_dt)

            # Seçili kodları ayrıştır: Portföy kaynakları ve Benchmarklar
            portfolio_sources: List[str] = []
            benchmarks: List[str] = []

            for code in self._selected_codes:
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

            # Backend analizi çalıştır
            dto = self._analysis_service.get_comparison_view(filter_state)

            # DTO'dan serileri ve etiketleri çıkar
            series_dict, code_to_label = ComparisonSeriesBuilder.build_global_series(dto, [])

            if not series_dict:
                self._chart_html = ""
                self._metrics_list = []
                self.chartHtmlChanged.emit()
                self.metricsListChanged.emit()
                return

            # Serileri takvim bazında hizala
            aligned = ComparisonService.align_financial_series(series_dict)
            if aligned.empty or len(aligned) < 2:
                self._chart_html = ""
                self._metrics_list = []
                self.chartHtmlChanged.emit()
                self.metricsListChanged.emit()
                return

            # Baz 100 normalize getiri hesabı
            first_row = aligned.iloc[0]
            normalized = (aligned.divide(first_row)) * 100.0
            normalized = normalized.replace([float('inf'), float('-inf')], float('nan'))
            normalized = normalized.ffill().bfill()

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
            self._metrics_list = metrics
            self.metricsListChanged.emit()

            # Chart HTML oluştur
            self._chart_html = self._build_chart_html(normalized)
            self.chartHtmlChanged.emit()

        except Exception as exc:
            logger.exception("Karşılaştırma hesaplaması başarısız: %s", exc)
            self.operationResult.emit(False, str(exc))
        finally:
            self._is_loading = False
            self.isLoadingChanged.emit()

    # ──────────────────────────── Internal Helpers ────────────────────────────

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
        # Tümü
        return date(2022, 1, 1)

    def _build_chart_html(self, normalized: pd.DataFrame) -> str:
        """LightweightCharts normalize getiri grafiği (Baz 100)."""
        palette = [
            "#2962ff", "#089981", "#f23645", "#ff9800",
            "#ab47bc", "#00bcd4", "#ff5722", "#4caf50",
            "#e91e63", "#3f51b5", "#009688", "#ffc107"
        ]

        datasets_js = []
        for i, col in enumerate(normalized.columns):
            color = palette[i % len(palette)]
            data_points = []
            series = normalized[col].dropna()
            for dt_val, val in series.items():
                if hasattr(dt_val, "strftime"):
                    time_str = dt_val.strftime("%Y-%m-%d")
                else:
                    time_str = str(dt_val)[:10]
                data_points.append(f"{{time:'{time_str}',value:{float(val):.2f}}}")

            datasets_js.append(f"""
                var s{i} = chart.addLineSeries({{
                    color: '{color}',
                    lineWidth: 2,
                    title: '{col}'
                }});
                s{i}.setData([{','.join(data_points)}]);
            """)

        return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
body {{ margin: 0; background: #131722; overflow: hidden; }}
#c {{ width: 100vw; height: 100vh; }}
</style>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
</head><body>
<div id="c"></div>
<script>
var chart = LightweightCharts.createChart(document.getElementById('c'), {{
    width: window.innerWidth,
    height: window.innerHeight,
    layout: {{ background: {{ color: '#131722' }}, textColor: '#9db2ce' }},
    grid: {{ vertLines: {{ color: '#1e222d' }}, horzLines: {{ color: '#1e222d' }} }},
    rightPriceScale: {{ borderColor: '#2a2e39', scaleMargins: {{ top: 0.1, bottom: 0.1 }} }},
    timeScale: {{ borderColor: '#2a2e39', timeVisible: false }},
    crosshair: {{ mode: 0 }}
}});
{''.join(datasets_js)}
chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
    chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
}});
</script></body></html>"""
