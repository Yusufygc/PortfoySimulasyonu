from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from src.domain.ports.services.i_market_data_client import IMarketDataClient

from .models import BenchmarkDefinition, BenchmarkSeries

logger = logging.getLogger(__name__)


class AnalysisBenchmarkService:
    DEFAULT_BENCHMARK_CODES = ["bist100", "gold", "usd", "deposit"]
    DEFAULT_DEPOSIT_RATE = Decimal("0.45")
    MARKET_BENCHMARK_CANDIDATES: Dict[str, Sequence[str]] = {
        "bist100": ("XU100.IS", "^XU100"),
        "usd": ("TRY=X", "USDTRY=X"),
    }
    GOLD_DIRECT_TICKERS: Sequence[str] = ("XAUTRY=X",)
    GOLD_USD_TICKERS: Sequence[str] = ("XAUUSD=X", "GC=F")

    def __init__(self, market_data_client: IMarketDataClient) -> None:
        self._market_data_client = market_data_client
        self._benchmarks: Dict[str, BenchmarkDefinition] = {
            "bist100": BenchmarkDefinition("bist100", "BIST 100", "market", "XU100.IS"),
            "gold": BenchmarkDefinition("gold", "Altin", "market", "GC=F"),
            "usd": BenchmarkDefinition("usd", "USD/TRY", "market", "TRY=X"),
            "deposit": BenchmarkDefinition("deposit", "Mevduat Faizi", "synthetic"),
        }

    def get_benchmark_definitions(self) -> List[BenchmarkDefinition]:
        return [self._benchmarks[code] for code in self.DEFAULT_BENCHMARK_CODES]

    def build_benchmark_series(
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
                elif definition.code == "gold":
                    points = self._build_gold_series(start_date, end_date)
                else:
                    points = self._build_market_series(definition, start_date, end_date)
            except Exception:
                logger.warning("Benchmark serisi olusturulamadi: %s", definition.code, exc_info=True)
                points = {}
            if not points:
                warnings.append(f"{definition.label} benchmark verisi alinamadi.")
                continue
            results.append(BenchmarkSeries(code=definition.code, label=definition.label, points=points))
        return results, warnings

    def _build_market_series(
        self,
        definition: BenchmarkDefinition,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        candidates = self._get_market_ticker_candidates(definition)
        points, _ = self._fetch_first_available_market_series(candidates, start_date, end_date)
        return points

    def _build_gold_series(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        direct_series, _ = self._fetch_first_available_market_series(self.GOLD_DIRECT_TICKERS, start_date, end_date)
        if direct_series:
            return direct_series

        gold_usd_series, _ = self._fetch_first_available_market_series(self.GOLD_USD_TICKERS, start_date, end_date)
        if not gold_usd_series:
            return {}

        usd_definition = self._benchmarks.get("usd")
        usd_candidates = self._get_market_ticker_candidates(usd_definition) if usd_definition is not None else []
        usd_try_series, _ = self._fetch_first_available_market_series(usd_candidates, start_date, end_date)
        if usd_try_series:
            combined = self._combine_series_by_date(gold_usd_series, usd_try_series)
            if combined:
                return combined

        return gold_usd_series

    def _get_market_ticker_candidates(self, definition: BenchmarkDefinition | None) -> List[str]:
        if definition is None:
            return []

        candidates: List[str] = []
        if definition.ticker:
            candidates.append(definition.ticker)
        for ticker in self.MARKET_BENCHMARK_CANDIDATES.get(definition.code, ()):
            if ticker not in candidates:
                candidates.append(ticker)
        return candidates

    def _fetch_first_available_market_series(
        self,
        candidates: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> tuple[Dict[date, Decimal], Optional[str]]:
        for ticker in candidates:
            try:
                points = self._market_data_client.get_price_series(ticker, start_date, end_date)
            except Exception:
                logger.debug("Benchmark ticker denemesi basarisiz: %s", ticker, exc_info=True)
                points = {}
            if points:
                return points, ticker
        return {}, None

    def _combine_series_by_date(
        self,
        left_series: Dict[date, Decimal],
        right_series: Dict[date, Decimal],
    ) -> Dict[date, Decimal]:
        shared_dates = sorted(set(left_series).intersection(right_series))
        return {
            point_date: left_series[point_date] * right_series[point_date]
            for point_date in shared_dates
        }

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

