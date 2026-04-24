from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.models.trade import Trade
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient


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


class AnalysisService:
    DEFAULT_BENCHMARK_CODES = ["bist100", "gold", "usd", "deposit"]
    DEFAULT_DEPOSIT_RATE = Decimal("0.45")
    SOURCE_DASHBOARD = "dashboard"
    SOURCE_MODEL_PREFIX = "model:"

    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        market_data_client: IMarketDataClient,
        model_portfolio_service=None,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._market_data_client = market_data_client
        self._model_portfolio_service = model_portfolio_service
        self._benchmarks: Dict[str, BenchmarkDefinition] = {
            "bist100": BenchmarkDefinition("bist100", "BIST 100", "market", "XU100.IS"),
            "gold": BenchmarkDefinition("gold", "Altın", "market", "GC=F"),
            "usd": BenchmarkDefinition("usd", "USD/TRY", "market", "TRY=X"),
            "deposit": BenchmarkDefinition("deposit", "Mevduat Faizi", "synthetic"),
        }

    def get_benchmark_definitions(self) -> List[BenchmarkDefinition]:
        return [self._benchmarks[code] for code in self.DEFAULT_BENCHMARK_CODES]

    def get_portfolio_options(self) -> List[PortfolioOption]:
        options = [PortfolioOption(code=self.SOURCE_DASHBOARD, label="Ana Portföy", kind="dashboard")]
        if self._model_portfolio_service is not None:
            for portfolio in self._model_portfolio_service.get_all_portfolios():
                options.append(
                    PortfolioOption(
                        code=f"{self.SOURCE_MODEL_PREFIX}{portfolio.id}",
                        label=portfolio.name,
                        kind="model",
                    )
                )
        return options

    def get_first_trade_date_for_source(self, source_code: str) -> Optional[date]:
        trades = self._get_source_trades(source_code)
        if not trades:
            return None
        return min(trade.trade_date for trade in trades)

    def get_stock_map_for_source(self, source_code: str) -> Dict[int, str]:
        trades = self._get_source_trades(source_code)
        stock_ids = sorted({trade.stock_id for trade in trades})
        return self._stock_repo.get_ticker_map_for_stock_ids(stock_ids)

    def get_overview(self, filter_state: AnalysisFilterState) -> AnalysisOverviewDTO:
        bundle = self._build_analysis_bundle(filter_state)
        position_snapshot = self._compute_position_snapshot(bundle["portfolio"])
        portfolio_series = bundle["portfolio_series"]
        primary_benchmark = bundle["benchmarks"][0] if bundle["benchmarks"] else None
        benchmark_gap = self._compute_relative_gap_pct(portfolio_series, primary_benchmark.points) if primary_benchmark else None

        top_position = max(position_snapshot, key=lambda item: item["weight"], default=None)
        best = max(position_snapshot, key=lambda item: item["return_pct"], default=None)
        worst = min(position_snapshot, key=lambda item: item["return_pct"], default=None)
        max_drawdown = self._compute_max_drawdown_pct(portfolio_series)
        concentration_label = self._get_concentration_label(
            sum(item["weight"] for item in sorted(position_snapshot, key=lambda x: x["weight"], reverse=True)[:3])
            if position_snapshot
            else None
        )

        insights = [
            self._build_benchmark_insight(primary_benchmark.label if primary_benchmark else "benchmark", benchmark_gap),
            f"Risk yoğunluğu: {concentration_label}",
        ]
        if best and best["label"] != "—":
            insights.append(f"En güçlü performans: {best['label']} (%{best['return_pct']:+.2f})")

        return AnalysisOverviewDTO(
            total_value=bundle["end_total_value"],
            period_return_pct=self._compute_return_pct(portfolio_series),
            benchmark_gap_pct=benchmark_gap,
            benchmark_label=primary_benchmark.label if primary_benchmark else "Benchmark",
            largest_position_label=top_position["label"] if top_position else "—",
            largest_position_weight_pct=top_position["weight"] if top_position else None,
            best_contributor_label=best["label"] if best else "—",
            best_contributor_pct=best["return_pct"] if best else None,
            worst_contributor_label=worst["label"] if worst else "—",
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
        portfolio_return = self._compute_return_pct(bundle["portfolio_series"])
        for benchmark in bundle["benchmarks"]:
            benchmark_return = self._compute_return_pct(benchmark.points)
            rel_gap = self._compute_relative_gap_pct(bundle["portfolio_series"], benchmark.points)
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
            other_return = self._compute_return_pct(portfolio_series.points)
            rel_gap = self._compute_relative_gap_pct(bundle["portfolio_series"], portfolio_series.points)
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
        position_snapshot = sorted(
            self._compute_position_snapshot(bundle["portfolio"]),
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
            volatility_pct=self._compute_volatility_pct(bundle["portfolio_series"]),
            max_drawdown_pct=self._compute_max_drawdown_pct(bundle["portfolio_series"]),
            concentration_label=self._get_concentration_label(top_three),
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

        trades = self._get_source_trades(filter_state.portfolio_source)
        portfolio_label = self._get_source_label(filter_state.portfolio_source)
        scoped_trades = [trade for trade in trades if trade.trade_date <= filter_state.end_date]
        stock_ids = self._resolve_stock_scope(scoped_trades, filter_state.selected_stock_ids)
        ticker_map = self._stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        portfolio = Portfolio.from_trades([trade for trade in scoped_trades if trade.stock_id in stock_ids])
        portfolio_series, position_values_end, warnings = self._compute_portfolio_series(
            scoped_trades,
            stock_ids,
            ticker_map,
            filter_state.start_date,
            filter_state.end_date,
            portfolio,
        )
        benchmark_series, benchmark_warnings = self._build_benchmark_series(
            filter_state.start_date,
            filter_state.end_date,
            filter_state.selected_benchmarks or self.DEFAULT_BENCHMARK_CODES,
        )
        warnings.extend(benchmark_warnings)
        stock_series, stock_warnings = self._build_stock_series(stock_ids, ticker_map, filter_state.start_date, filter_state.end_date)
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

    def _get_source_trades(self, source_code: str) -> List[Trade]:
        if source_code == self.SOURCE_DASHBOARD:
            return list(self._portfolio_repo.get_all_trades())
        if source_code.startswith(self.SOURCE_MODEL_PREFIX) and self._model_portfolio_service is not None:
            portfolio_id = int(source_code.split(":", 1)[1])
            model_trades = self._model_portfolio_service.get_portfolio_trades(portfolio_id)
            converted: List[Trade] = []
            for trade in model_trades:
                if trade.side == ModelTradeSide.BUY:
                    converted.append(
                        Trade.create_buy(
                            stock_id=trade.stock_id,
                            trade_date=trade.trade_date,
                            quantity=trade.quantity,
                            price=trade.price,
                            trade_time=trade.trade_time,
                        )
                    )
                else:
                    converted.append(
                        Trade.create_sell(
                            stock_id=trade.stock_id,
                            trade_date=trade.trade_date,
                            quantity=trade.quantity,
                            price=trade.price,
                            trade_time=trade.trade_time,
                        )
                    )
            return converted
        return []

    def _get_source_label(self, source_code: str) -> str:
        for option in self.get_portfolio_options():
            if option.code == source_code:
                return option.label
        return "Portföy"

    def _build_comparison_portfolio_series(self, filter_state: AnalysisFilterState) -> List[BenchmarkSeries]:
        results: List[BenchmarkSeries] = []
        for source_code in filter_state.comparison_portfolio_sources:
            if source_code == filter_state.portfolio_source:
                continue
            trades = self._get_source_trades(source_code)
            scoped_trades = [trade for trade in trades if trade.trade_date <= filter_state.end_date]
            stock_ids = self._resolve_stock_scope(scoped_trades, [])
            ticker_map = self._stock_repo.get_ticker_map_for_stock_ids(stock_ids)
            portfolio = Portfolio.from_trades(scoped_trades)
            portfolio_series, _, _ = self._compute_portfolio_series(
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
                        label=self._get_source_label(source_code),
                        points=portfolio_series,
                    )
                )
        return results

    def _validate_filter_state(self, filter_state: AnalysisFilterState) -> None:
        if filter_state.start_date > filter_state.end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

    def _resolve_stock_scope(self, trades: Iterable[Trade], selected_stock_ids: Sequence[int]) -> List[int]:
        selected = [stock_id for stock_id in selected_stock_ids if stock_id]
        if selected:
            return sorted(set(selected))
        return sorted({trade.stock_id for trade in trades})

    def _compute_portfolio_series(
        self,
        trades: List[Trade],
        stock_ids: Sequence[int],
        ticker_map: Dict[int, str],
        start_date: date,
        end_date: date,
        portfolio: Portfolio,
    ) -> tuple[Dict[date, Decimal], Dict[int, Decimal], List[str]]:
        if not stock_ids:
            return {}, {}, []

        prices_by_stock: Dict[int, Dict[date, Decimal]] = {
            stock_id: {
                daily.price_date: daily.close_price
                for daily in self._price_repo.get_price_series(stock_id, start_date, end_date)
            }
            for stock_id in stock_ids
        }
        last_prices: Dict[int, Optional[Decimal]] = {}
        warnings: List[str] = []
        for stock_id in stock_ids:
            previous_price = self._price_repo.get_last_price_before(stock_id, start_date)
            last_prices[stock_id] = previous_price.close_price if previous_price else None
            if not prices_by_stock[stock_id]:
                warnings.append(f"{ticker_map.get(stock_id, str(stock_id))} için tarih aralığında fiyat verisi bulunamadı.")

        trades_before = [trade for trade in trades if trade.trade_date < start_date and trade.stock_id in stock_ids]
        current_positions = {
            stock_id: Position.from_trades(stock_id, [trade for trade in trades_before if trade.stock_id == stock_id])
            for stock_id in stock_ids
        }
        trades_by_date: Dict[date, List[Trade]] = {}
        for trade in trades:
            if trade.stock_id not in stock_ids:
                continue
            if start_date <= trade.trade_date <= end_date:
                trades_by_date.setdefault(trade.trade_date, []).append(trade)

        portfolio_series: Dict[date, Decimal] = {}
        current_day = start_date
        while current_day <= end_date:
            for trade in sorted(trades_by_date.get(current_day, []), key=lambda item: item.trade_time or time.min):
                current_positions[trade.stock_id].apply_trade(trade)
            total_value = Decimal("0")
            for stock_id in stock_ids:
                day_price = prices_by_stock[stock_id].get(current_day)
                if day_price is not None:
                    last_prices[stock_id] = day_price
                price = last_prices[stock_id]
                if price is None:
                    continue
                total_value += current_positions[stock_id].market_value(price)
            portfolio_series[current_day] = total_value
            current_day += timedelta(days=1)

        position_values_end: Dict[int, Decimal] = {}
        for stock_id in stock_ids:
            position = portfolio.positions.get(stock_id)
            if not position or position.total_quantity <= 0:
                continue
            price = last_prices.get(stock_id)
            if price is None:
                continue
            position_values_end[stock_id] = position.market_value(price)
        return portfolio_series, position_values_end, warnings

    def _build_stock_series(
        self,
        stock_ids: Sequence[int],
        ticker_map: Dict[int, str],
        start_date: date,
        end_date: date,
    ) -> tuple[Dict[str, Dict[date, Decimal]], List[str]]:
        series_map: Dict[str, Dict[date, Decimal]] = {}
        warnings: List[str] = []
        for stock_id in stock_ids:
            ticker = ticker_map.get(stock_id)
            if not ticker:
                continue
            points = {
                daily.price_date: daily.close_price
                for daily in self._price_repo.get_price_series(stock_id, start_date, end_date)
            }
            if not points:
                warnings.append(f"{ticker} için karşılaştırma serisi üretilemedi.")
                continue
            series_map[ticker] = points
        return series_map, warnings

    def _build_benchmark_series(
        self,
        start_date: date,
        end_date: date,
        selected_codes: Sequence[str],
    ) -> tuple[List[BenchmarkSeries], List[str]]:
        results: List[BenchmarkSeries] = []
        warnings: List[str] = []
        for code in selected_codes:
            definition = self._benchmarks.get(code)
            if definition is None:
                continue
            try:
                if definition.kind == "synthetic":
                    points = self._build_deposit_series(start_date, end_date)
                else:
                    points = self._market_data_client.get_price_series(definition.ticker, start_date, end_date)
            except Exception:
                points = {}
            if not points:
                warnings.append(f"{definition.label} benchmark verisi alınamadı.")
                continue
            results.append(BenchmarkSeries(code=definition.code, label=definition.label, points=points))
        return results, warnings

    def _build_deposit_series(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        annual_rate = Decimal(os.getenv("ANALYSIS_DEPOSIT_ANNUAL_RATE", str(self.DEFAULT_DEPOSIT_RATE)))
        daily_rate = annual_rate / Decimal("365")
        value = Decimal("100")
        result: Dict[date, Decimal] = {}
        current_day = start_date
        while current_day <= end_date:
            result[current_day] = value
            value = value * (Decimal("1") + daily_rate)
            current_day += timedelta(days=1)
        return result

    def _compute_position_snapshot(self, portfolio: Portfolio) -> List[Dict[str, object]]:
        ticker_map = self._stock_repo.get_ticker_map_for_stock_ids(list(portfolio.positions.keys()))
        total_value = sum(
            (
                getattr(position, "_analysis_current_value", Decimal("0"))
                for position in portfolio.positions.values()
                if position.total_quantity > 0
            ),
            Decimal("0"),
        )
        items: List[Dict[str, object]] = []
        for stock_id, position in portfolio.positions.items():
            if position.total_quantity <= 0:
                continue
            current_value = getattr(position, "_analysis_current_value", Decimal("0"))
            weight = float((current_value / total_value) * Decimal("100")) if total_value > 0 else 0.0
            return_pct = None
            if position.total_cost > 0:
                return_pct = float(((current_value - position.total_cost) / position.total_cost) * Decimal("100"))
            items.append(
                {
                    "label": ticker_map.get(stock_id, str(stock_id)),
                    "current_value": current_value,
                    "cost_value": position.total_cost,
                    "weight": weight,
                    "return_pct": return_pct if return_pct is not None else 0.0,
                }
            )
        return items

    def _compute_return_pct(self, series: Dict[date, Decimal]) -> Optional[float]:
        if not series:
            return None
        values = [value for value in series.values() if value is not None]
        start = next((value for value in values if value > 0), None)
        end = values[-1] if values else None
        if start is None or end is None or start == 0:
            return None
        return float(((end - start) / start) * Decimal("100"))

    def _compute_relative_gap_pct(
        self,
        portfolio_series: Dict[date, Decimal],
        benchmark_series: Dict[date, Decimal],
    ) -> Optional[float]:
        portfolio_return = self._compute_return_pct(portfolio_series)
        benchmark_return = self._compute_return_pct(benchmark_series)
        if portfolio_return is None or benchmark_return is None:
            return None
        return portfolio_return - benchmark_return

    def _compute_daily_return_vector(self, series: Dict[date, Decimal]) -> List[float]:
        values = [float(value) for value in series.values() if value is not None and value > 0]
        returns: List[float] = []
        for prev, curr in zip(values, values[1:]):
            if prev == 0:
                continue
            returns.append((curr - prev) / prev)
        return returns

    def _compute_volatility_pct(self, series: Dict[date, Decimal]) -> Optional[float]:
        returns = self._compute_daily_return_vector(series)
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
        return math.sqrt(variance) * math.sqrt(252) * 100

    def _compute_max_drawdown_pct(self, series: Dict[date, Decimal]) -> Optional[float]:
        values = [float(value) for value in series.values() if value is not None and value > 0]
        if not values:
            return None
        peak = values[0]
        max_drawdown = 0.0
        for value in values:
            peak = max(peak, value)
            if peak == 0:
                continue
            drawdown = ((value - peak) / peak) * 100
            max_drawdown = min(max_drawdown, drawdown)
        return max_drawdown

    def _get_concentration_label(self, top_three_weight_pct: Optional[float]) -> str:
        if top_three_weight_pct is None:
            return "Veri Yok"
        if top_three_weight_pct >= 75:
            return "Yüksek"
        if top_three_weight_pct >= 50:
            return "Orta"
        return "Düşük"

    def _build_benchmark_insight(self, benchmark_label: str, gap: Optional[float]) -> str:
        if gap is None:
            return f"{benchmark_label} kıyası için yeterli veri yok."
        if gap >= 0:
            return f"Portföy {benchmark_label} kıyasının %{gap:.2f} üzerinde."
        return f"Portföy {benchmark_label} kıyasının %{abs(gap):.2f} gerisinde."
