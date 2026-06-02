from __future__ import annotations

import logging
from datetime import date

from src.application.services.analysis.models import AnalysisFilterState

logger = logging.getLogger(__name__)

BENCHMARK_CODES = {"bist100", "gold", "silver", "usd", "euro", "deposit", "cpi"}


class ComparisonFilterStateBuilder:
    """Resolve selected asset codes into comparison service filter state."""

    def __init__(self, page, analysis_service) -> None:
        self.page = page
        self.analysis_service = analysis_service

    def expand_holdings(self, selected_codes: list[str]) -> tuple[list[str], bool]:
        has_holdings_trigger = False
        new_selected_codes = list(selected_codes)

        for code in selected_codes:
            if not code.startswith("holdings:"):
                continue
            has_holdings_trigger = True
            portfolio_code = code.split(":", 1)[1]
            try:
                stock_map = self.analysis_service.get_stock_map_for_source(portfolio_code)
                if not stock_map:
                    continue
                if portfolio_code not in new_selected_codes:
                    new_selected_codes.append(portfolio_code)
                for stock_id, ticker in stock_map.items():
                    stock_id_str = str(stock_id)
                    self.page._asset_labels[stock_id_str] = ticker
                    if stock_id_str not in new_selected_codes:
                        new_selected_codes.append(stock_id_str)
            except Exception as exc:
                logger.error("Error loading holdings in refresh: %s", exc)

        return new_selected_codes, has_holdings_trigger

    def build(self, selected_codes: list[str], start_date: date, end_date: date) -> tuple[AnalysisFilterState, list[int]]:
        portfolio_sources: list[str] = []
        benchmarks: list[str] = []
        stock_ids: list[int] = []

        for code in selected_codes:
            if code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:"):
                portfolio_sources.append(code)
            elif code in BENCHMARK_CODES:
                benchmarks.append(code)
            else:
                try:
                    stock_ids.append(int(code))
                except ValueError:
                    pass

        primary_source = portfolio_sources[0] if portfolio_sources else "dashboard"
        return (
            AnalysisFilterState(
                start_date=start_date,
                end_date=end_date,
                selected_stock_ids=stock_ids,
                selected_benchmarks=benchmarks,
                portfolio_source=primary_source,
                comparison_portfolio_sources=portfolio_sources,
                currency_mode="TL",
            ),
            stock_ids,
        )
