from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Sequence

from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.repositories.i_cash_movement_repo import ICashMovementRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient

from .analysis_bundle_builder import AnalysisBundleBuilder
from .benchmark_service import AnalysisBenchmarkService, EvdsSeriesProvider
from .comparison_portfolio_series_builder import ComparisonPortfolioSeriesBuilder
from .currency_conversion_service import CurrencyConversionService
from .models import (
    AllocationItem,
    AllocationRiskDTO,
    AnalysisFilterState,
    AnalysisOverviewDTO,
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
    compute_sharpe_ratio,
    compute_beta,
    compute_alpha,
)
from .source_resolver import AnalysisSourceResolver


class AnalysisService:
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        market_data_client: IMarketDataClient,
        evds_client: EvdsSeriesProvider | None = None,
        cash_movement_repo: Optional[ICashMovementRepository] = None,
        model_portfolio_service=None,
    ) -> None:
        self._stock_repo = stock_repo
        self._cash_movement_repo = cash_movement_repo
        self._source_resolver = AnalysisSourceResolver(
            portfolio_repo=portfolio_repo,
            stock_repo=stock_repo,
            model_portfolio_service=model_portfolio_service,
        )
        self._series_builder = PortfolioSeriesBuilder(
            price_repo=price_repo,
            stock_repo=stock_repo,
        )
        self._benchmark_service = AnalysisBenchmarkService(
            market_data_client=market_data_client,
            evds_client=evds_client
        )
        self._currency_service = CurrencyConversionService()
        self._bundle_builder = AnalysisBundleBuilder(
            source_resolver=self._source_resolver,
            series_builder=self._series_builder,
            benchmark_service=self._benchmark_service,
            currency_service=self._currency_service,
            cash_movement_repo=cash_movement_repo,
        )
        self._comparison_series_builder = ComparisonPortfolioSeriesBuilder(
            source_resolver=self._source_resolver,
            series_builder=self._series_builder,
            currency_service=self._currency_service,
        )

    def get_benchmark_definitions(self):
        return self._benchmark_service.get_benchmark_definitions()

    def get_portfolio_options(self):
        return self._source_resolver.get_portfolio_options()

    def get_first_trade_date_for_source(self, source_code: str) -> Optional[date]:
        return self._source_resolver.get_first_trade_date_for_source(source_code)

    def get_stock_map_for_source(self, source_code: str) -> Dict[int, str]:
        return self._source_resolver.get_stock_map_for_source(source_code)

    def get_overview(self, filter_state: AnalysisFilterState, bundle: Optional[Dict[str, object]] = None) -> AnalysisOverviewDTO:
        if bundle is None:
            bundle = self._build_analysis_bundle(filter_state)
        ticker_map = self._series_builder.get_ticker_map(list(bundle["portfolio"].positions.keys()))
        position_snapshot = compute_position_snapshot(
            bundle["portfolio"],
            ticker_map,
            bundle["position_values_end"],
        )
        portfolio_series = bundle["portfolio_series"]
        primary_benchmark = bundle["benchmarks"][0] if bundle["benchmarks"] else None
        benchmark_gap = (
            compute_relative_gap_pct(portfolio_series, primary_benchmark.points)
            if primary_benchmark
            else None
        )

        top_position = max(position_snapshot, key=lambda item: item["weight"], default=None)
        best = max(position_snapshot, key=lambda item: item["return_pct"], default=None)
        worst = min(position_snapshot, key=lambda item: item["return_pct"], default=None) if len(position_snapshot) > 1 else None
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
            currency_mode=filter_state.currency_mode,
        )

    def get_comparison_view(
        self,
        filter_state: AnalysisFilterState,
        selected_benchmarks: Optional[Sequence[str]] = None,
        bundle: Optional[Dict[str, object]] = None,
    ) -> ComparisonViewDTO:
        benchmark_codes = list(selected_benchmarks) if selected_benchmarks is not None else filter_state.selected_benchmarks
        state = AnalysisFilterState(
            start_date=filter_state.start_date,
            end_date=filter_state.end_date,
            selected_stock_ids=list(filter_state.selected_stock_ids),
            selected_benchmarks=list(benchmark_codes),
            portfolio_source=filter_state.portfolio_source,
            comparison_portfolio_sources=list(filter_state.comparison_portfolio_sources),
        )
        if bundle is None:
            bundle = self._build_analysis_bundle(state)
        portfolio_return = compute_return_pct(bundle["portfolio_series"])
        metrics = self._benchmark_comparison_metrics(bundle, portfolio_return)
        comparison_portfolios = self._build_comparison_portfolio_series(state, bundle=bundle)
        metrics.extend(self._portfolio_comparison_metrics(bundle, comparison_portfolios, portfolio_return))

        return ComparisonViewDTO(
            portfolio_series=bundle["portfolio_series"],
            benchmark_series=bundle["benchmarks"],
            stock_series=bundle["stock_series"],
            comparison_metrics=metrics,
            comparison_portfolios=comparison_portfolios,
            current_portfolio_label=bundle["portfolio_label"],
            warnings=bundle["warnings"],
        )

    @staticmethod
    def _benchmark_comparison_metrics(bundle: Dict[str, object], portfolio_return) -> List[ComparisonMetric]:
        return [
            ComparisonMetric(
                label=benchmark.label,
                portfolio_return_pct=portfolio_return,
                benchmark_return_pct=compute_return_pct(benchmark.points),
                relative_gap_pct=compute_relative_gap_pct(bundle["portfolio_series"], benchmark.points),
            )
            for benchmark in bundle["benchmarks"]
        ]

    @staticmethod
    def _portfolio_comparison_metrics(
        bundle: Dict[str, object],
        comparison_portfolios: Sequence,
        portfolio_return,
    ) -> List[ComparisonMetric]:
        return [
            ComparisonMetric(
                label=portfolio_series.label,
                portfolio_return_pct=portfolio_return,
                benchmark_return_pct=compute_return_pct(portfolio_series.points),
                relative_gap_pct=compute_relative_gap_pct(bundle["portfolio_series"], portfolio_series.points),
            )
            for portfolio_series in comparison_portfolios
        ]

    def get_allocation_risk_view(self, filter_state: AnalysisFilterState, bundle: Optional[Dict[str, object]] = None) -> AllocationRiskDTO:
        if bundle is None:
            bundle = self._build_analysis_bundle(filter_state)
        ticker_map = self._series_builder.get_ticker_map(list(bundle["portfolio"].positions.keys()))
        position_snapshot = sorted(
            compute_position_snapshot(bundle["portfolio"], ticker_map, bundle["position_values_end"]),
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
        primary_benchmark_series = bundle["benchmarks"][0].points if bundle.get("benchmarks") else None
        
        return AllocationRiskDTO(
            items=items,
            top_three_weight_pct=top_three,
            volatility_pct=compute_volatility_pct(bundle["portfolio_series"]),
            max_drawdown_pct=compute_max_drawdown_pct(bundle["portfolio_series"]),
            sharpe_ratio=compute_sharpe_ratio(bundle["portfolio_series"]),
            beta=compute_beta(bundle["portfolio_series"], primary_benchmark_series) if primary_benchmark_series else None,
            alpha=compute_alpha(bundle["portfolio_series"], primary_benchmark_series) if primary_benchmark_series else None,
            concentration_label=get_concentration_label(top_three),
            warnings=bundle["warnings"],
        )

    def get_page_payload(self, filter_state: AnalysisFilterState) -> Dict[str, object]:
        bundle = self._build_analysis_bundle(filter_state)
        return {
            "overview": self.get_overview(filter_state, bundle=bundle),
            "comparison": self.get_comparison_view(filter_state, filter_state.selected_benchmarks, bundle=bundle),
            "risk": self.get_allocation_risk_view(filter_state, bundle=bundle),
        }

    def _build_analysis_bundle(self, filter_state: AnalysisFilterState) -> Dict[str, object]:
        self._validate_filter_state(filter_state)
        return self._bundle_builder.build(filter_state)

    def _apply_currency_mode(
        self, 
        series: dict, 
        currency_mode: str, 
        usd_try_series: dict, 
        cpi_series: dict,
        is_normalized: bool = False
    ) -> dict:
        return self._currency_service.apply_currency_mode(
            series,
            currency_mode,
            usd_try_series,
            cpi_series,
            is_normalized=is_normalized,
        )

    def _build_comparison_portfolio_series(
        self,
        filter_state: AnalysisFilterState,
        bundle: Optional[Dict[str, object]] = None,
    ) -> list:
        return self._comparison_series_builder.build(filter_state, bundle=bundle)

    def _validate_filter_state(self, filter_state: AnalysisFilterState) -> None:
        if filter_state.start_date > filter_state.end_date:
            raise ValueError("Baslangic tarihi bitis tarihinden sonra olamaz.")
