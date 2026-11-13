"""
PortfolioAnalyticsService — "Portföy Analiz ve Kıyaslama Laboratuvarı" birleşik servisi (bkz. plan §5.2).

`AnalysisService` (bundle/DTO orkestrasyonu: overview, benchmark kıyaslama, tahsis/risk) ile
`ComparisonService` (saf pandas panel hesapları: hizalama, drawdown, dönemsel getiri, risk/getiri
dağılımı) ve `risk_metrics.py`'nin genişletilmiş metriklerini (Sortino/Calmar/Omega/VaR/CVaR/
R²/Tracking Error/Aylık Getiri Isı Haritası — Faz 2 b4'te eklendi, henüz hiçbir UI'ya bağlı değil)
tek servis altında toplar.

Mevcut `AnalysisPage`/`ComparisonPage`, `container.analysis_service` ile çalışmaya devam eder —
bu facade onları değiştirmez, üstüne ekler (Stock360Service ile aynı desen, bkz. §5.1).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

import pandas as pd

from src.application.services.analysis.analysis_service import AnalysisService
from src.application.services.analysis.comparison_service import ComparisonService
from src.application.services.analysis.models import (
    AllocationRiskDTO,
    AnalysisFilterState,
    AnalysisOverviewDTO,
    ComparisonViewDTO,
)
from src.application.services.analysis.risk_metrics import (
    compute_alpha,
    compute_beta,
    compute_calmar_ratio,
    compute_conditional_var_pct,
    compute_monthly_returns_matrix,
    compute_omega_ratio,
    compute_r_squared,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_tracking_error,
    compute_value_at_risk_pct,
)


@dataclass(frozen=True)
class ChartPanelsDTO:
    """6 grafik panelinin ham verisi (plan §5.2 madde 1-6)."""
    aligned_series: pd.DataFrame                        # Panel 1: hizalanmış ham seriler
    drawdowns: pd.DataFrame                              # Panel 3: drawdown/underwater
    periodic_returns: pd.DataFrame                       # Panel 4: dönemsel (aylık) getiri
    risk_return_metrics: Dict[str, Dict[str, float]]     # Panel 5: risk/getiri saçılımı
    comparison: ComparisonViewDTO                        # Panel 2 (dönem özeti) ve 6 (treemap) ham verisi


@dataclass(frozen=True)
class ExtendedRiskMetricsDTO:
    """Ek risk/performans metrikleri (plan §5.2 madde 7)."""
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    omega_ratio: Optional[float]
    value_at_risk_95_pct: Optional[float]
    conditional_var_95_pct: Optional[float]
    beta: Optional[float]
    alpha: Optional[float]
    r_squared: Optional[float]
    tracking_error_pct: Optional[float]
    monthly_returns_matrix: Dict[int, Dict[int, float]]
    benchmark_label: Optional[str]


def _to_pd_series(points: Dict[date, Decimal]) -> pd.Series:
    """DatetimeIndex'li seri üretir — `ComparisonService.calculate_periodic_returns()` `resample()`
    çağırdığından düz `date` index'i kabul etmez (bkz. `comparison_series_builder.py` ile aynı desen)."""
    if not points:
        return pd.Series(dtype=float)
    dates = sorted(points.keys())
    return pd.Series([float(points[d]) for d in dates], index=[pd.Timestamp(d) for d in dates])


def _collect_named_series(comparison: ComparisonViewDTO) -> Dict[str, pd.Series]:
    series_dict: Dict[str, pd.Series] = {
        comparison.current_portfolio_label: _to_pd_series(comparison.portfolio_series),
    }
    for benchmark in comparison.benchmark_series:
        series_dict[benchmark.label] = _to_pd_series(benchmark.points)
    for ticker, points in comparison.stock_series.items():
        series_dict[ticker] = _to_pd_series(points)
    for portfolio in comparison.comparison_portfolios:
        series_dict[portfolio.label] = _to_pd_series(portfolio.points)
    return series_dict


class PortfolioAnalyticsService:
    """Portföy analiz/kıyaslama görünümü — mevcut AnalysisService'e delege + yeni panel/metrik hesapları."""

    def __init__(self, analysis_service: AnalysisService) -> None:
        self._analysis_service = analysis_service

    # ------------------------------------------------------------------
    # AnalysisService pass-through (mevcut sözleşme, davranış değişmedi)
    # ------------------------------------------------------------------

    def get_benchmark_definitions(self):
        return self._analysis_service.get_benchmark_definitions()

    def get_portfolio_options(self):
        return self._analysis_service.get_portfolio_options()

    def get_first_trade_date_for_source(self, source_code: str) -> Optional[date]:
        return self._analysis_service.get_first_trade_date_for_source(source_code)

    def get_stock_map_for_source(self, source_code: str) -> Dict[int, str]:
        return self._analysis_service.get_stock_map_for_source(source_code)

    def get_overview(self, filter_state: AnalysisFilterState, bundle=None) -> AnalysisOverviewDTO:
        return self._analysis_service.get_overview(filter_state, bundle=bundle)

    def get_comparison_view(
        self,
        filter_state: AnalysisFilterState,
        selected_benchmarks: Optional[Sequence[str]] = None,
        bundle=None,
    ) -> ComparisonViewDTO:
        return self._analysis_service.get_comparison_view(filter_state, selected_benchmarks, bundle=bundle)

    def get_allocation_risk_view(self, filter_state: AnalysisFilterState, bundle=None) -> AllocationRiskDTO:
        return self._analysis_service.get_allocation_risk_view(filter_state, bundle=bundle)

    # ------------------------------------------------------------------
    # Yeni: 6 grafik paneli — ComparisonService'in saf pandas hesapları
    # ------------------------------------------------------------------

    def get_chart_panels(
        self,
        filter_state: AnalysisFilterState,
        selected_benchmarks: Optional[Sequence[str]] = None,
        comparison: Optional[ComparisonViewDTO] = None,
    ) -> ChartPanelsDTO:
        comparison = comparison or self.get_comparison_view(filter_state, selected_benchmarks)
        aligned = ComparisonService.align_financial_series(_collect_named_series(comparison))
        return ChartPanelsDTO(
            aligned_series=aligned,
            drawdowns=ComparisonService.calculate_drawdowns(aligned),
            periodic_returns=ComparisonService.calculate_periodic_returns(aligned),
            risk_return_metrics=ComparisonService.calculate_risk_return_metrics(aligned),
            comparison=comparison,
        )

    # ------------------------------------------------------------------
    # Yeni: genişletilmiş risk/performans metrikleri (plan §5.2 madde 7)
    # ------------------------------------------------------------------

    def get_extended_risk_metrics(
        self,
        filter_state: AnalysisFilterState,
        selected_benchmarks: Optional[Sequence[str]] = None,
        comparison: Optional[ComparisonViewDTO] = None,
    ) -> ExtendedRiskMetricsDTO:
        comparison = comparison or self.get_comparison_view(filter_state, selected_benchmarks)
        portfolio_series = comparison.portfolio_series
        primary_benchmark = comparison.benchmark_series[0] if comparison.benchmark_series else None
        benchmark_points = primary_benchmark.points if primary_benchmark else None

        beta = alpha = r_squared = tracking_error = None
        if benchmark_points:
            beta = compute_beta(portfolio_series, benchmark_points)
            alpha = compute_alpha(portfolio_series, benchmark_points)
            r_squared = compute_r_squared(portfolio_series, benchmark_points)
            tracking_error = compute_tracking_error(portfolio_series, benchmark_points)

        return ExtendedRiskMetricsDTO(
            sharpe_ratio=compute_sharpe_ratio(portfolio_series),
            sortino_ratio=compute_sortino_ratio(portfolio_series),
            calmar_ratio=compute_calmar_ratio(portfolio_series),
            omega_ratio=compute_omega_ratio(portfolio_series),
            value_at_risk_95_pct=compute_value_at_risk_pct(portfolio_series),
            conditional_var_95_pct=compute_conditional_var_pct(portfolio_series),
            beta=beta,
            alpha=alpha,
            r_squared=r_squared,
            tracking_error_pct=tracking_error,
            monthly_returns_matrix=compute_monthly_returns_matrix(portfolio_series),
            benchmark_label=primary_benchmark.label if primary_benchmark else None,
        )
