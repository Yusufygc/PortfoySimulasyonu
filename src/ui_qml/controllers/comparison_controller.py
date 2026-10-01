"""
ComparisonController — Karşılaştırma Laboratuvarı QML controller'ı.

Sorumluluk:
- Karşılaştırılabilir varlık listesini sağlama (portföyler + benchmarklar)
- Seçili varlıklar ve tarih aralığı ile normalize getiri serisi oluşturma
- Drawdown ve Risk-Getiri metriklerini hesaplama
- Tüm sonuçları QML property'lerine reaktif olarak yansıtma
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

logger = logging.getLogger(__name__)


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
        self._comparison_service = getattr(container, "comparison_service", None)
        self._price_repo = container.price_repo
        self._stock_repo = container.stock_repo

        # State
        self._asset_options: List[Dict[str, str]] = []
        self._selected_codes: List[str] = []
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
        """Karşılaştırılabilir varlık listesini yükler."""
        try:
            options: List[Dict[str, str]] = []

            # Portföyler
            portfolios = self._analysis_service.get_portfolio_options()
            for p in portfolios:
                options.append({"code": p.code, "label": p.label, "kind": p.kind})

            # Benchmarklar
            benchmarks = self._analysis_service.get_benchmark_definitions()
            for b in benchmarks:
                options.append({"code": b.code, "label": b.label, "kind": b.kind})

            self._asset_options = options
            self.assetOptionsChanged.emit()

            # İlk açılışta XU100'ü otomatik seç
            if not self._selected_codes and options:
                xu100 = next((o for o in options if "xu100" in o["code"].lower()), None)
                if xu100:
                    self._selected_codes = [xu100["code"]]
                elif len(options) > 0:
                    self._selected_codes = [options[0]["code"]]
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
        """Seçili varlıklarla karşılaştırma hesaplamasını çalıştırır."""
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

            # Her varlık için fiyat serisini topla
            import pandas as pd
            import numpy as np

            series_dict: Dict[str, pd.Series] = {}
            label_map: Dict[str, str] = {}

            for code in self._selected_codes:
                label, series = self._get_price_series(code, start_dt, end_dt)
                if series is not None and len(series) > 1:
                    series_dict[code] = series
                    label_map[code] = label

            if not series_dict:
                self._chart_html = ""
                self._metrics_list = []
                self.chartHtmlChanged.emit()
                self.metricsListChanged.emit()
                self._is_loading = False
                self.isLoadingChanged.emit()
                return

            # Serileri hizala ve normalize et (baz=100)
            from src.application.services.analysis.comparison_service import ComparisonService
            aligned = ComparisonService.align_financial_series(series_dict)
            normalized = (aligned / aligned.iloc[0]) * 100.0

            # Risk-Getiri Metrikleri
            risk_return = ComparisonService.calculate_risk_return_metrics(aligned)

            metrics = []
            for code, label in label_map.items():
                rm = risk_return.get(code, {})
                metrics.append({
                    "code": code,
                    "label": label,
                    "totalReturn": round(rm.get("total_return_pct", 0.0), 2),
                    "volatility": round(rm.get("annual_volatility_pct", 0.0), 2),
                })
            self._metrics_list = metrics
            self.metricsListChanged.emit()

            # Chart HTML oluştur
            self._chart_html = self._build_chart_html(normalized, label_map)
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
        # Tümü — en geniş tarih
        return date(2020, 1, 1)

    def _get_price_series(self, code: str, start_dt: date, end_dt: date):
        """Kod (benchmark/portföy/hisse) için fiyat serisini çeker."""
        import pandas as pd

        # Benchmark kodları (xu100, usd_try, gold_tl, vb.)
        benchmarks = self._analysis_service.get_benchmark_definitions()
        bm = next((b for b in benchmarks if b.code == code), None)
        if bm and bm.ticker:
            stock = self._stock_repo.get_stock_by_ticker(bm.ticker.upper())
            if stock and stock.id:
                rows = self._price_repo.get_price_series(stock.id, start_dt, end_dt)
                if rows:
                    dates = [r.price_date for r in rows]
                    values = [float(r.close_price) for r in rows if r.close_price]
                    if dates and values and len(dates) == len(values):
                        return bm.label, pd.Series(values, index=dates)

        # Portföy kaynaklı — basit hisse araması dene
        stock = self._stock_repo.get_stock_by_ticker(code.upper())
        if stock and stock.id:
            rows = self._price_repo.get_price_series(stock.id, start_dt, end_dt)
            if rows:
                dates = [r.price_date for r in rows]
                values = [float(r.close_price) for r in rows if r.close_price]
                if dates and values and len(dates) == len(values):
                    return stock.ticker, pd.Series(values, index=dates)

        return code, None

    def _build_chart_html(self, normalized, label_map) -> str:
        """Lightweight.js tabanlı normalize getiri grafiği HTML'i üretir."""
        colors = ["#2962ff", "#089981", "#f23645", "#ff9800", "#9c27b0", "#00bcd4", "#ff5722", "#4caf50"]

        datasets_js = []
        for i, code in enumerate(normalized.columns):
            label = label_map.get(code, code)
            color = colors[i % len(colors)]
            data_points = []
            for dt_val, val in normalized[code].dropna().items():
                if hasattr(dt_val, "isoformat"):
                    ts = f"new Date('{dt_val.isoformat()}').getTime()/1000"
                else:
                    ts = "0"
                data_points.append(f"{{time:{ts},value:{val:.2f}}}")
            datasets_js.append(f"""
                var s{i} = chart.addLineSeries({{color:'{color}',lineWidth:2,title:'{label}'}});
                s{i}.setData([{','.join(data_points)}]);
            """)

        return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>body{{margin:0;background:#131722;overflow:hidden}}</style>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
</head><body>
<div id="c" style="width:100%;height:100%"></div>
<script>
var chart = LightweightCharts.createChart(document.getElementById('c'),{{
    width:document.body.clientWidth,
    height:document.body.clientHeight,
    layout:{{background:{{color:'#131722'}},textColor:'#9db2ce'}},
    grid:{{vertLines:{{color:'#1e222d'}},horzLines:{{color:'#1e222d'}}}},
    rightPriceScale:{{borderColor:'#2a2e39'}},
    timeScale:{{borderColor:'#2a2e39',timeVisible:false}},
    crosshair:{{mode:0}},
}});
{''.join(datasets_js)}
chart.timeScale().fitContent();
new ResizeObserver(()=>chart.applyOptions({{width:document.body.clientWidth,height:document.body.clientHeight}})).observe(document.body);
</script></body></html>"""
