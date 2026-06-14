from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely

from .benchmark_service import AnalysisBenchmarkService
from .currency_conversion_service import CurrencyConversionService
from .models import AnalysisFilterState, BenchmarkSeries
from .portfolio_series_builder import PortfolioSeriesBuilder
from .source_resolver import AnalysisSourceResolver


class AnalysisBundleBuilder:
    def __init__(
        self,
        source_resolver: AnalysisSourceResolver,
        series_builder: PortfolioSeriesBuilder,
        benchmark_service: AnalysisBenchmarkService,
        currency_service: CurrencyConversionService,
        cash_movement_repo=None,
    ) -> None:
        self._source_resolver = source_resolver
        self._series_builder = series_builder
        self._benchmark_service = benchmark_service
        self._currency_service = currency_service
        self._cash_movement_repo = cash_movement_repo

    def build(self, filter_state: AnalysisFilterState) -> Dict[str, object]:
        warnings: List[str] = []
        data = self._resolve_trade_data(filter_state)
        series = self._compute_series_and_benchmarks(filter_state, data, warnings)
        end_total_value = next(reversed(series["raw_portfolio_series"].values())) if series["raw_portfolio_series"] else Decimal("0")
        return {
            "portfolio": data["build_result"].portfolio,
            "portfolio_series": series["twr_series"],
            "benchmarks": series["benchmark_series"],
            "stock_series": series["stock_series"],
            "position_values_end": series["position_values_end"],
            "end_total_value": end_total_value,
            "warnings": warnings,
            "portfolio_label": data["portfolio_label"],
            "usd_series_dict": series["usd_series"],
            "cpi_series_dict": series["cpi_series"],
        }

    def _resolve_trade_data(self, filter_state: AnalysisFilterState) -> dict:
        trades = self._source_resolver.get_source_trades(filter_state.portfolio_source)
        portfolio_label = self._source_resolver.get_source_label(filter_state.portfolio_source)
        scoped_trades = [trade for trade in trades if trade.trade_date <= filter_state.end_date]
        display_stock_ids = self._series_builder.resolve_stock_scope(
            scoped_trades, filter_state.selected_stock_ids, as_of=filter_state.end_date,
        )
        valuation_stock_ids = self._series_builder.resolve_valuation_stock_scope(
            scoped_trades, filter_state.selected_stock_ids, filter_state.start_date, filter_state.end_date,
        )
        trade_stock_ids = display_stock_ids if filter_state.selected_stock_ids else None
        ticker_map = self._series_builder.get_ticker_map(sorted(set(display_stock_ids) | set(valuation_stock_ids)))
        build_result = build_portfolio_safely(
            [trade for trade in scoped_trades if not trade_stock_ids or trade.stock_id in trade_stock_ids]
        )
        return {
            "portfolio_label": portfolio_label,
            "display_stock_ids": display_stock_ids,
            "valuation_stock_ids": valuation_stock_ids,
            "trade_stock_ids": trade_stock_ids,
            "ticker_map": ticker_map,
            "build_result": build_result,
            "cash_movements": self._cash_movements_for(filter_state),
        }

    def _compute_series_and_benchmarks(self, filter_state: AnalysisFilterState, data: dict, warnings: list) -> dict:
        build_result = data["build_result"]
        ticker_map = data["ticker_map"]
        portfolio_series, twr_series, position_values_end, series_warnings = self._series_builder.compute_portfolio_series(
            build_result.valid_trades, data["cash_movements"], data["valuation_stock_ids"],
            ticker_map, filter_state.start_date, filter_state.end_date,
            build_result.portfolio, trade_stock_ids=data["trade_stock_ids"],
        )
        warnings.extend(series_warnings)
        raw_benchmarks, benchmark_warnings = self._benchmark_service.build_benchmark_series(
            filter_state.start_date, filter_state.end_date, self._needed_benchmarks(filter_state),
        )
        warnings.extend(benchmark_warnings)
        usd_series = next((b.points for b in raw_benchmarks if b.code == "usd"), {})
        cpi_series = next((b.points for b in raw_benchmarks if b.code == "cpi"), {})
        raw_portfolio_series = self._currency_service.apply_currency_mode(portfolio_series, filter_state.currency_mode, usd_series, cpi_series)
        twr_series = self._currency_service.apply_currency_mode(twr_series, filter_state.currency_mode, usd_series, cpi_series, is_normalized=True)
        benchmark_series = self._converted_benchmarks(filter_state, raw_benchmarks, usd_series, cpi_series)
        stock_series, stock_warnings = self._converted_stock_series(filter_state, data["display_stock_ids"], ticker_map, usd_series, cpi_series)
        warnings.extend(stock_warnings)
        return {
            "twr_series": twr_series, "raw_portfolio_series": raw_portfolio_series,
            "position_values_end": position_values_end, "benchmark_series": benchmark_series,
            "stock_series": stock_series, "usd_series": usd_series, "cpi_series": cpi_series,
        }

    def _cash_movements_for(self, filter_state: AnalysisFilterState) -> list:
        if filter_state.portfolio_source == "dashboard" and self._cash_movement_repo:
            return list(self._cash_movement_repo.get_all_movements())
        return []

    @staticmethod
    def _needed_benchmarks(filter_state: AnalysisFilterState) -> List[str]:
        needed = list(filter_state.selected_benchmarks)
        if filter_state.currency_mode == "USD" and "usd" not in needed:
            needed.append("usd")
        if filter_state.currency_mode == "REAL" and "cpi" not in needed:
            needed.append("cpi")
        return needed

    def _converted_benchmarks(
        self,
        filter_state: AnalysisFilterState,
        raw_benchmarks: List[BenchmarkSeries],
        usd_series: dict,
        cpi_series: dict,
    ) -> List[BenchmarkSeries]:
        benchmarks: List[BenchmarkSeries] = []
        for benchmark in raw_benchmarks:
            if benchmark.code not in filter_state.selected_benchmarks:
                continue
            points = self._currency_service.apply_currency_mode(
                benchmark.points,
                filter_state.currency_mode,
                usd_series,
                cpi_series,
                is_normalized=True,
            )
            benchmarks.append(BenchmarkSeries(code=benchmark.code, label=benchmark.label, points=points))
        return benchmarks

    def _converted_stock_series(
        self,
        filter_state: AnalysisFilterState,
        stock_ids: List[int],
        ticker_map: dict,
        usd_series: dict,
        cpi_series: dict,
    ) -> tuple[Dict[int, dict], List[str]]:
        stock_series, warnings = self._series_builder.build_stock_series(
            stock_ids,
            ticker_map,
            filter_state.start_date,
            filter_state.end_date,
        )
        return {
            stock_id: self._currency_service.apply_currency_mode(
                series,
                filter_state.currency_mode,
                usd_series,
                cpi_series,
            )
            for stock_id, series in stock_series.items()
        }, warnings
