from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from src.domain.models.portfolio import Portfolio
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient

from .benchmark_service import AnalysisBenchmarkService
from .models import (
    AllocationItem,
    AllocationRiskDTO,
    AnalysisFilterState,
    AnalysisOverviewDTO,
    BenchmarkSeries,
    ComparisonMetric,
    ComparisonViewDTO,
)
from .portfolio_series_builder import PortfolioSeriesBuilder
from .risk_metrics import (
    build_benchmark_insight,
    compute_max_drawdown_pct,
    compute_position_snapshot,
    compute_relative_gap_pct,
    compute_return_pct,
    compute_volatility_pct,
    get_concentration_label,
)
from .source_resolver import AnalysisSourceResolver


class AnalysisService:
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        market_data_client: IMarketDataClient,
        model_portfolio_service=None,
    ) -> None:
        self._stock_repo = stock_repo
        self._source_resolver = AnalysisSourceResolver(
            portfolio_repo=portfolio_repo,
            stock_repo=stock_repo,
            model_portfolio_service=model_portfolio_service,
        )
        self._series_builder = PortfolioSeriesBuilder(
            price_repo=price_repo,
            stock_repo=stock_repo,
        )
        self._benchmark_service = AnalysisBenchmarkService(market_data_client=market_data_client)

    def get_benchmark_definitions(self):
        return self._benchmark_service.get_benchmark_definitions()

    def get_portfolio_options(self):
        return self._source_resolver.get_portfolio_options()

    def get_first_trade_date_for_source(self, source_code: str) -> Optional[date]:
        return self._source_resolver.get_first_trade_date_for_source(source_code)

    def get_stock_map_for_source(self, source_code: str) -> Dict[int, str]:
        return self._source_resolver.get_stock_map_for_source(source_code)

    def get_overview(self, filter_state: AnalysisFilterState) -> AnalysisOverviewDTO:
        bundle = self._build_analysis_bundle(filter_state)
        ticker_map = self._series_builder.get_ticker_map(list(bundle["portfolio"].positions.keys()))
        position_snapshot = compute_position_snapshot(bundle["portfolio"], ticker_map)
        portfolio_series = bundle["portfolio_series"]
        primary_benchmark = bundle["benchmarks"][0] if bundle["benchmarks"] else None
        benchmark_gap = (
            compute_relative_gap_pct(portfolio_series, primary_benchmark.points)
            if primary_benchmark
            else None
        )

        top_position = max(position_snapshot, key=lambda item: item["weight"], default=None)
        best = max(position_snapshot, key=lambda item: item["return_pct"], default=None)
        worst = min(position_snapshot, key=lambda item: item["return_pct"], default=None)
        max_drawdown = compute_max_drawdown_pct(portfolio_series)
        concentration_label = get_concentration_label(
            sum(item["weight"] for item in sorted(position_snapshot, key=lambda x: x["weight"], reverse=True)[:3])
            if position_snapshot
            else None
        )

        insights = [
            build_benchmark_insight(primary_benchmark.label if primary_benchmark else "benchmark", benchmark_gap),
            f"Risk yogunlugu: {concentration_label}",
        ]
        if best and best["label"] != "-":
            insights.append(f"En guclu performans: {best['label']} (%{best['return_pct']:+.2f})")

        return AnalysisOverviewDTO(
            total_value=bundle["end_total_value"],
            period_return_pct=compute_return_pct(portfolio_series),
            benchmark_gap_pct=benchmark_gap,
            benchmark_label=primary_benchmark.label if primary_benchmark else "Benchmark",
            largest_position_label=top_position["label"] if top_position else "-",
            largest_position_weight_pct=top_position["weight"] if top_position else None,
            best_contributor_label=best["label"] if best else "-",
            best_contributor_pct=best["return_pct"] if best else None,
            worst_contributor_label=worst["label"] if worst else "-",
            worst_contributor_pct=worst["return_pct"] if worst else None,
            max_drawdown_pct=max_drawdown,
            insights=insights,
            warnings=bundle["warnings"],
            portfolio_label=bundle["portfolio_label"],
        )

    def get_comparison_view(
        self,
        filter_state: AnalysisFilterState,
        selected_benchmarks: Optional[Sequence[str]] = None,
    ) -> ComparisonViewDTO:
        benchmark_codes = list(selected_benchmarks) if selected_benchmarks is not None else filter_state.selected_benchmarks
        state = AnalysisFilterState(
            start_date=filter_state.start_date,
            end_date=filter_state.end_date,
            selected_stock_ids=list(filter_state.selected_stock_ids),
            view_mode=filter_state.view_mode,
            selected_benchmarks=list(benchmark_codes),
            portfolio_source=filter_state.portfolio_source,
            comparison_portfolio_sources=list(filter_state.comparison_portfolio_sources),
        )
        bundle = self._build_analysis_bundle(state)
        metrics: List[ComparisonMetric] = []
        portfolio_return = compute_return_pct(bundle["portfolio_series"])
        for benchmark in bundle["benchmarks"]:
            benchmark_return = compute_return_pct(benchmark.points)
            rel_gap = compute_relative_gap_pct(bundle["portfolio_series"], benchmark.points)
            metrics.append(
                ComparisonMetric(
                    label=benchmark.label,
                    portfolio_return_pct=portfolio_return,
                    benchmark_return_pct=benchmark_return,
                    relative_gap_pct=rel_gap,
                )
            )

        comparison_portfolios = self._build_comparison_portfolio_series(state)
        for portfolio_series in comparison_portfolios:
            other_return = compute_return_pct(portfolio_series.points)
            rel_gap = compute_relative_gap_pct(bundle["portfolio_series"], portfolio_series.points)
            metrics.append(
                ComparisonMetric(
                    label=portfolio_series.label,
                    portfolio_return_pct=portfolio_return,
                    benchmark_return_pct=other_return,
                    relative_gap_pct=rel_gap,
                )
            )

        return ComparisonViewDTO(
            portfolio_series=bundle["portfolio_series"],
            benchmark_series=bundle["benchmarks"],
            stock_series=bundle["stock_series"],
            comparison_metrics=metrics,
            comparison_portfolios=comparison_portfolios,
            current_portfolio_label=bundle["portfolio_label"],
            warnings=bundle["warnings"],
        )

    def get_allocation_risk_view(self, filter_state: AnalysisFilterState) -> AllocationRiskDTO:
        bundle = self._build_analysis_bundle(filter_state)
        ticker_map = self._series_builder.get_ticker_map(list(bundle["portfolio"].positions.keys()))
        position_snapshot = sorted(
            compute_position_snapshot(bundle["portfolio"], ticker_map),
            key=lambda item: item["weight"],
            reverse=True,
        )
        items = [
            AllocationItem(
                label=item["label"],
                cost_value=float(item["cost_value"]),
                current_value=float(item["current_value"]),
                weight_pct=item["weight"],
            )
            for item in position_snapshot
        ]
        top_three = sum(item["weight"] for item in position_snapshot[:3]) if position_snapshot else None
        return AllocationRiskDTO(
            items=items,
            top_three_weight_pct=top_three,
            volatility_pct=compute_volatility_pct(bundle["portfolio_series"]),
            max_drawdown_pct=compute_max_drawdown_pct(bundle["portfolio_series"]),
            concentration_label=get_concentration_label(top_three),
            warnings=bundle["warnings"],
        )

    def get_page_payload(self, filter_state: AnalysisFilterState) -> Dict[str, object]:
        return {
            "overview": self.get_overview(filter_state),
            "comparison": self.get_comparison_view(filter_state, filter_state.selected_benchmarks),
            "risk": self.get_allocation_risk_view(filter_state),
        }

    def _build_analysis_bundle(self, filter_state: AnalysisFilterState) -> Dict[str, object]:
        self._validate_filter_state(filter_state)

        trades = self._source_resolver.get_source_trades(filter_state.portfolio_source)
        portfolio_label = self._source_resolver.get_source_label(filter_state.portfolio_source)
        scoped_trades = [trade for trade in trades if trade.trade_date <= filter_state.end_date]
        stock_ids = self._series_builder.resolve_stock_scope(scoped_trades, filter_state.selected_stock_ids)
        ticker_map = self._series_builder.get_ticker_map(stock_ids)

        portfolio = Portfolio.from_trades([trade for trade in scoped_trades if trade.stock_id in stock_ids])
        portfolio_series, position_values_end, warnings = self._series_builder.compute_portfolio_series(
            scoped_trades,
            stock_ids,
            ticker_map,
            filter_state.start_date,
            filter_state.end_date,
            portfolio,
        )
        benchmark_series, benchmark_warnings = self._benchmark_service.build_benchmark_series(
            filter_state.start_date,
            filter_state.end_date,
            filter_state.selected_benchmarks or self._benchmark_service.DEFAULT_BENCHMARK_CODES,
        )
        warnings.extend(benchmark_warnings)
        stock_series, stock_warnings = self._series_builder.build_stock_series(
            stock_ids,
            ticker_map,
            filter_state.start_date,
            filter_state.end_date,
        )
        warnings.extend(stock_warnings)

        for stock_id, value in position_values_end.items():
            if stock_id in portfolio.positions:
                setattr(portfolio.positions[stock_id], "_analysis_current_value", value)

        end_total_value = next(reversed(portfolio_series.values())) if portfolio_series else Decimal("0")
        return {
            "portfolio": portfolio,
            "portfolio_series": portfolio_series,
            "benchmarks": benchmark_series,
            "stock_series": stock_series,
            "end_total_value": end_total_value,
            "warnings": warnings,
            "portfolio_label": portfolio_label,
        }

    def _build_comparison_portfolio_series(self, filter_state: AnalysisFilterState) -> List[BenchmarkSeries]:
        results: List[BenchmarkSeries] = []
        for source_code in filter_state.comparison_portfolio_sources:
            if source_code == filter_state.portfolio_source:
                continue
            trades = self._source_resolver.get_source_trades(source_code)
            scoped_trades = [trade for trade in trades if trade.trade_date <= filter_state.end_date]
            stock_ids = self._series_builder.resolve_stock_scope(scoped_trades, [])
            ticker_map = self._series_builder.get_ticker_map(stock_ids)
            portfolio = Portfolio.from_trades(scoped_trades)
            portfolio_series, _, _ = self._series_builder.compute_portfolio_series(
                scoped_trades,
                stock_ids,
                ticker_map,
                filter_state.start_date,
                filter_state.end_date,
                portfolio,
            )
            if portfolio_series:
                results.append(
                    BenchmarkSeries(
                        code=source_code,
                        label=self._source_resolver.get_source_label(source_code),
                        points=portfolio_series,
                    )
                )
        return results

    def _validate_filter_state(self, filter_state: AnalysisFilterState) -> None:
        if filter_state.start_date > filter_state.end_date:
            raise ValueError("Baslangic tarihi bitis tarihinden sonra olamaz.")

