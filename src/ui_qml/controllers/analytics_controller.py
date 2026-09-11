"""
AnalyticsController — AnalyticsView'un veri köprüsü (bkz. plan §7.3 madde 4, d4).

Karşılaştırma Laboratuvarı'nın 6 grafik panelinden ilk 5'i + gelişmiş risk/
performans paneli burada QML'e bağlanır (6. panel, Treemap, plan §7.4'te ayrı
bir alt-görev olarak not edildiği için ayrı adımda eklenecek — bkz. plan §9.5).

Backend: `PortfolioAnalyticsService.get_chart_panels()`/`get_extended_risk_metrics()`
(§5.2'de zaten hazırlanmış facade metodları) — hesap mantığı burada yeniden
yazılmadı, sadece QML-bindable şekle (paralel listeler + float property'ler)
dönüştürüldü. Filtre state inşası `DashboardController._build_filter_state()`
ile aynı desen (varsayılan: dashboard portföyü, BIST 100 benchmark, ilk işlem
tarihinden bugüne).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List, Optional

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.application.services.analysis.models import AnalysisFilterState

_DEFAULT_LOOKBACK_DAYS = 365
_DEFAULT_BENCHMARK = "bist100"
_MISSING_MONTH_SENTINEL = -9999.0


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


class AnalyticsController(QObject):
    """Karşılaştırma Laboratuvarı'nın 5 grafik paneli + gelişmiş risk paneli."""

    performanceChanged = Signal()
    summaryChanged = Signal()
    drawdownChanged = Signal()
    periodicReturnsChanged = Signal()
    scatterChanged = Signal()
    treemapChanged = Signal()
    riskMetricsChanged = Signal()
    monthlyHeatmapChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container

        self._benchmark_label = ""
        self._portfolio_values: List[float] = []
        self._benchmark_values: List[float] = []

        self._summary_labels: List[str] = []
        self._summary_portfolio_return_pct: List[float] = []
        self._summary_benchmark_return_pct: List[float] = []
        self._summary_relative_gap_pct: List[float] = []

        self._drawdown_values: List[float] = []

        self._periodic_return_labels: List[str] = []
        self._periodic_return_values: List[float] = []

        self._scatter_labels: List[str] = []
        self._scatter_volatility_pct: List[float] = []
        self._scatter_return_pct: List[float] = []

        self._treemap_items: List[dict] = []

        self._sharpe_ratio = 0.0
        self._sortino_ratio = 0.0
        self._calmar_ratio = 0.0
        self._omega_ratio = 0.0
        self._value_at_risk_95_pct = 0.0
        self._conditional_var_95_pct = 0.0
        self._beta = 0.0
        self._alpha = 0.0
        self._r_squared = 0.0
        self._tracking_error_pct = 0.0

        self._monthly_heatmap_years: List[int] = []
        self._monthly_heatmap_rows: List[List[float]] = []

        self.refresh()

    # ------------------------------------------------------------------
    # Panel 1: Kümülatif Getiri & Performans (Baz 100 normalize)
    # ------------------------------------------------------------------

    @Property(str, notify=performanceChanged)
    def benchmarkLabel(self) -> str:
        return self._benchmark_label

    @Property("QVariantList", notify=performanceChanged)
    def portfolioPerformanceValues(self) -> List[float]:
        return list(self._portfolio_values)

    @Property("QVariantList", notify=performanceChanged)
    def benchmarkPerformanceValues(self) -> List[float]:
        return list(self._benchmark_values)

    # ------------------------------------------------------------------
    # Panel 2: Dönem Sonu Getiri Özeti Tablosu
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=summaryChanged)
    def summaryLabels(self) -> List[str]:
        return list(self._summary_labels)

    @Property("QVariantList", notify=summaryChanged)
    def summaryPortfolioReturnPct(self) -> List[float]:
        return list(self._summary_portfolio_return_pct)

    @Property("QVariantList", notify=summaryChanged)
    def summaryBenchmarkReturnPct(self) -> List[float]:
        return list(self._summary_benchmark_return_pct)

    @Property("QVariantList", notify=summaryChanged)
    def summaryRelativeGapPct(self) -> List[float]:
        return list(self._summary_relative_gap_pct)

    # ------------------------------------------------------------------
    # Panel 3: Maksimum Drawdown
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=drawdownChanged)
    def drawdownValues(self) -> List[float]:
        return list(self._drawdown_values)

    # ------------------------------------------------------------------
    # Panel 4: Dönemsel (Aylık) Getiri Karşılaştırma
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=periodicReturnsChanged)
    def periodicReturnLabels(self) -> List[str]:
        return list(self._periodic_return_labels)

    @Property("QVariantList", notify=periodicReturnsChanged)
    def periodicReturnValues(self) -> List[float]:
        return list(self._periodic_return_values)

    # ------------------------------------------------------------------
    # Panel 5: Risk / Getiri Dağılımı (Scatter)
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=scatterChanged)
    def scatterLabels(self) -> List[str]:
        return list(self._scatter_labels)

    @Property("QVariantList", notify=scatterChanged)
    def scatterVolatilityPct(self) -> List[float]:
        return list(self._scatter_volatility_pct)

    @Property("QVariantList", notify=scatterChanged)
    def scatterReturnPct(self) -> List[float]:
        return list(self._scatter_return_pct)

    # ------------------------------------------------------------------
    # Panel 6: Treemap Getiri Katkı Haritası
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=treemapChanged)
    def treemapItems(self) -> List[dict]:
        return [dict(item) for item in self._treemap_items]

    # ------------------------------------------------------------------
    # Panel 7: Gelişmiş Risk/Performans Paneli
    # ------------------------------------------------------------------

    @Property(float, notify=riskMetricsChanged)
    def sharpeRatio(self) -> float:
        return self._sharpe_ratio

    @Property(float, notify=riskMetricsChanged)
    def sortinoRatio(self) -> float:
        return self._sortino_ratio

    @Property(float, notify=riskMetricsChanged)
    def calmarRatio(self) -> float:
        return self._calmar_ratio

    @Property(float, notify=riskMetricsChanged)
    def omegaRatio(self) -> float:
        return self._omega_ratio

    @Property(float, notify=riskMetricsChanged)
    def valueAtRisk95Pct(self) -> float:
        return self._value_at_risk_95_pct

    @Property(float, notify=riskMetricsChanged)
    def conditionalVar95Pct(self) -> float:
        return self._conditional_var_95_pct

    @Property(float, notify=riskMetricsChanged)
    def beta(self) -> float:
        return self._beta

    @Property(float, notify=riskMetricsChanged)
    def alpha(self) -> float:
        return self._alpha

    @Property(float, notify=riskMetricsChanged)
    def rSquared(self) -> float:
        return self._r_squared

    @Property(float, notify=riskMetricsChanged)
    def trackingErrorPct(self) -> float:
        return self._tracking_error_pct

    # Aylık Getiri Isı Haritası — eksik ay `_MISSING_MONTH_SENTINEL` ile işaretlenir
    # (QML tarafı bu değeri "veri yok" hücresi olarak yorumlar, bkz. AnalyticsView.qml).
    @Property("QVariantList", notify=monthlyHeatmapChanged)
    def monthlyHeatmapYears(self) -> List[int]:
        return list(self._monthly_heatmap_years)

    @Property("QVariantList", notify=monthlyHeatmapChanged)
    def monthlyHeatmapRows(self) -> List[List[float]]:
        return [list(row) for row in self._monthly_heatmap_rows]

    # ------------------------------------------------------------------
    # Veri yenileme
    # ------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        analytics = self._container.portfolio_analytics_service
        filter_state = self._build_filter_state()
        panels = analytics.get_chart_panels(filter_state)
        extended = analytics.get_extended_risk_metrics(filter_state, comparison=panels.comparison)

        self._refresh_performance(panels)
        self._refresh_summary(panels)
        self._refresh_drawdown(panels)
        self._refresh_periodic_returns(panels)
        self._refresh_scatter(panels)
        self._refresh_treemap(panels)
        self._refresh_risk_metrics(extended)
        self._refresh_monthly_heatmap(extended)

    def _build_filter_state(self) -> AnalysisFilterState:
        today = date.today()
        analytics = self._container.portfolio_analytics_service
        start = analytics.get_first_trade_date_for_source("dashboard") or (today - timedelta(days=_DEFAULT_LOOKBACK_DAYS))
        return AnalysisFilterState(
            start_date=start,
            end_date=today,
            portfolio_source="dashboard",
            selected_benchmarks=[_DEFAULT_BENCHMARK],
        )

    def _refresh_performance(self, panels) -> None:
        comparison = panels.comparison
        portfolio_label = comparison.current_portfolio_label
        benchmark_label = comparison.benchmark_series[0].label if comparison.benchmark_series else ""

        aligned = panels.aligned_series
        portfolio_series = _normalized_base_100(aligned[portfolio_label]) if portfolio_label in aligned else []
        benchmark_series = _normalized_base_100(aligned[benchmark_label]) if benchmark_label in aligned else []

        self._benchmark_label = benchmark_label
        self._portfolio_values = portfolio_series
        self._benchmark_values = benchmark_series
        self.performanceChanged.emit()

    def _refresh_summary(self, panels) -> None:
        metrics = panels.comparison.comparison_metrics
        self._summary_labels = [m.label for m in metrics]
        self._summary_portfolio_return_pct = [_to_float(m.portfolio_return_pct) for m in metrics]
        self._summary_benchmark_return_pct = [_to_float(m.benchmark_return_pct) for m in metrics]
        self._summary_relative_gap_pct = [_to_float(m.relative_gap_pct) for m in metrics]
        self.summaryChanged.emit()

    def _refresh_drawdown(self, panels) -> None:
        portfolio_label = panels.comparison.current_portfolio_label
        drawdowns = panels.drawdowns
        if portfolio_label in drawdowns:
            self._drawdown_values = [float(v) for v in drawdowns[portfolio_label].tolist()]
        else:
            self._drawdown_values = []
        self.drawdownChanged.emit()

    def _refresh_periodic_returns(self, panels) -> None:
        portfolio_label = panels.comparison.current_portfolio_label
        periodic_returns = panels.periodic_returns
        if portfolio_label in periodic_returns:
            series = periodic_returns[portfolio_label]
            self._periodic_return_labels = [ts.strftime("%Y-%m") for ts in series.index]
            self._periodic_return_values = [float(v) for v in series.tolist()]
        else:
            self._periodic_return_labels = []
            self._periodic_return_values = []
        self.periodicReturnsChanged.emit()

    def _refresh_scatter(self, panels) -> None:
        risk_return = panels.risk_return_metrics
        self._scatter_labels = list(risk_return.keys())
        self._scatter_volatility_pct = [risk_return[label]["annual_volatility_pct"] for label in self._scatter_labels]
        self._scatter_return_pct = [risk_return[label]["total_return_pct"] for label in self._scatter_labels]
        self.scatterChanged.emit()

    def _refresh_treemap(self, panels) -> None:
        # Ağırlık formülü mevcut QtWidgets ComparisonPage'in treemap'iyle BİREBİR aynı
        # (bkz. src/ui/pages/comparison/utils/chart_renderer.py) — sıfır getirili varlıklar
        # da görünür kalsın diye taban ağırlık 1.0'a sabitlenir, hiçbir şey icat edilmedi.
        risk_return = panels.risk_return_metrics
        self._treemap_items = [
            {
                "label": label,
                "weight": max(abs(metrics["total_return_pct"]), 1.0),
                "value": metrics["total_return_pct"],
            }
            for label, metrics in risk_return.items()
        ]
        self.treemapChanged.emit()

    def _refresh_risk_metrics(self, extended) -> None:
        self._sharpe_ratio = _to_float(extended.sharpe_ratio)
        self._sortino_ratio = _to_float(extended.sortino_ratio)
        self._calmar_ratio = _to_float(extended.calmar_ratio)
        self._omega_ratio = _to_float(extended.omega_ratio)
        self._value_at_risk_95_pct = _to_float(extended.value_at_risk_95_pct)
        self._conditional_var_95_pct = _to_float(extended.conditional_var_95_pct)
        self._beta = _to_float(extended.beta)
        self._alpha = _to_float(extended.alpha)
        self._r_squared = _to_float(extended.r_squared)
        self._tracking_error_pct = _to_float(extended.tracking_error_pct)
        self.riskMetricsChanged.emit()

    def _refresh_monthly_heatmap(self, extended) -> None:
        matrix = extended.monthly_returns_matrix
        years = sorted(matrix.keys())
        rows = [
            [matrix[year].get(month, _MISSING_MONTH_SENTINEL) for month in range(1, 13)]
            for year in years
        ]
        self._monthly_heatmap_years = years
        self._monthly_heatmap_rows = rows
        self.monthlyHeatmapChanged.emit()


def _normalized_base_100(series) -> List[float]:
    """Bir pandas Series'i baz 100 endekse çevirir (ilk değer=100) — portföy ile
    benchmark'ı mutlak TL/endeks farklarından bağımsız aynı grafikte kıyaslamak için
    (plan §7.3 madde 1 "Normalize Baz 100 Modu")."""
    values = [float(v) for v in series.tolist()]
    if not values or values[0] == 0:
        return values
    base = values[0]
    return [v / base * 100.0 for v in values]
