from __future__ import annotations

from typing import Dict, List

from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely

from .currency_conversion_service import CurrencyConversionService
from .models import AnalysisFilterState, BenchmarkSeries
from .portfolio_series_builder import PortfolioSeriesBuilder
from .source_resolver import AnalysisSourceResolver


class ComparisonPortfolioSeriesBuilder:
    def __init__(
        self,
        source_resolver: AnalysisSourceResolver,
        series_builder: PortfolioSeriesBuilder,
        currency_service: CurrencyConversionService,
    ) -> None:
        self._source_resolver = source_resolver
        self._series_builder = series_builder
        self._currency_service = currency_service

    def build(
        self,
        filter_state: AnalysisFilterState,
        bundle: Dict[str, object] | None = None,
    ) -> List[BenchmarkSeries]:
        results: List[BenchmarkSeries] = []
        primary_source = self._source_resolver.normalize_source_code(filter_state.portfolio_source)
        for source_code in filter_state.comparison_portfolio_sources:
            source_code = self._source_resolver.normalize_source_code(source_code)
            if source_code == primary_source:
                continue
            series = self._build_source_series(source_code, filter_state)
            if not series:
                continue
            results.append(
                BenchmarkSeries(
                    code=source_code,
                    label=self._source_resolver.get_source_label(source_code),
                    points=self._convert_series(series, filter_state, bundle),
                )
            )
        return results

    def _build_source_series(
        self,
        source_code: str,
        filter_state: AnalysisFilterState,
    ) -> dict:
        trades = self._source_resolver.get_source_trades(source_code)
        scoped_trades = [trade for trade in trades if trade.trade_date <= filter_state.end_date]
        stock_ids = self._series_builder.resolve_valuation_stock_scope(
            scoped_trades,
            [],
            filter_state.start_date,
            filter_state.end_date,
        )
        trade_stock_ids = sorted({trade.stock_id for trade in scoped_trades})
        ticker_map = self._series_builder.get_ticker_map(stock_ids)
        build_result = build_portfolio_safely(scoped_trades)
        portfolio_series, _, _ = self._series_builder.compute_portfolio_series(
            build_result.valid_trades,
            [],
            stock_ids,
            ticker_map,
            filter_state.start_date,
            filter_state.end_date,
            build_result.portfolio,
            trade_stock_ids=trade_stock_ids,
        )
        return portfolio_series

    def _convert_series(
        self,
        portfolio_series: dict,
        filter_state: AnalysisFilterState,
        bundle: Dict[str, object] | None,
    ) -> dict:
        usd_series = bundle.get("usd_series_dict", {}) if bundle else {}
        cpi_series = bundle.get("cpi_series_dict", {}) if bundle else {}
        return self._currency_service.apply_currency_mode(
            portfolio_series,
            filter_state.currency_mode,
            usd_series,
            cpi_series,
            is_normalized=True,
        )
