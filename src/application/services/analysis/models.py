from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AnalysisFilterState:
    start_date: date
    end_date: date
    selected_stock_ids: List[int] = field(default_factory=list)
    view_mode: str = "portfolio"
    selected_benchmarks: List[str] = field(default_factory=list)
    portfolio_source: str = "dashboard"
    comparison_portfolio_sources: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PortfolioOption:
    code: str
    label: str
    kind: str


@dataclass(frozen=True)
class BenchmarkDefinition:
    code: str
    label: str
    kind: str
    ticker: Optional[str] = None


@dataclass(frozen=True)
class PortfolioSeriesPoint:
    point_date: date
    total_value: Decimal


@dataclass(frozen=True)
class BenchmarkSeries:
    code: str
    label: str
    points: Dict[date, Decimal]


@dataclass(frozen=True)
class AnalysisOverviewDTO:
    total_value: Decimal
    period_return_pct: Optional[float]
    benchmark_gap_pct: Optional[float]
    benchmark_label: str
    largest_position_label: str
    largest_position_weight_pct: Optional[float]
    best_contributor_label: str
    best_contributor_pct: Optional[float]
    worst_contributor_label: str
    worst_contributor_pct: Optional[float]
    max_drawdown_pct: Optional[float]
    insights: List[str]
    warnings: List[str]
    portfolio_label: str


@dataclass(frozen=True)
class ComparisonMetric:
    label: str
    portfolio_return_pct: Optional[float]
    benchmark_return_pct: Optional[float]
    relative_gap_pct: Optional[float]


@dataclass(frozen=True)
class ComparisonViewDTO:
    portfolio_series: Dict[date, Decimal]
    benchmark_series: List[BenchmarkSeries]
    stock_series: Dict[str, Dict[date, Decimal]]
    comparison_metrics: List[ComparisonMetric]
    comparison_portfolios: List[BenchmarkSeries]
    current_portfolio_label: str
    warnings: List[str]


@dataclass(frozen=True)
class AllocationItem:
    label: str
    cost_value: float
    current_value: float
    weight_pct: float


@dataclass(frozen=True)
class AllocationRiskDTO:
    items: List[AllocationItem]
    top_three_weight_pct: Optional[float]
    volatility_pct: Optional[float]
    max_drawdown_pct: Optional[float]
    concentration_label: str
    warnings: List[str]

