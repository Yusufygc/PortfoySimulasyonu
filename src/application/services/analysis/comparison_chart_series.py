from __future__ import annotations

import pandas as pd


class ComparisonSeriesBuilder:
    """Build chart series and label mappings from comparison DTOs."""

    @staticmethod
    def build_global_series(dto, selected_stock_ids: list[int]) -> tuple[dict[str, pd.Series], dict[str, str]]:
        series_dict: dict[str, pd.Series] = {}
        code_to_label: dict[str, str] = {}

        if dto.portfolio_series:
            p_series = ComparisonSeriesBuilder._series_from_points(
                dto.portfolio_series,
                dto.current_portfolio_label,
            )
            series_dict[dto.current_portfolio_label] = p_series
            code_to_label["dashboard"] = dto.current_portfolio_label

        for cp in dto.comparison_portfolios:
            if cp.points:
                series_dict[cp.label] = ComparisonSeriesBuilder._series_from_points(cp.points, cp.label)
                code_to_label[cp.code] = cp.label
                code_to_label[f"portfolio:{cp.code}"] = cp.label

        for benchmark in dto.benchmark_series:
            if benchmark.points:
                series_dict[benchmark.label] = ComparisonSeriesBuilder._series_from_points(
                    benchmark.points,
                    benchmark.label,
                )
                code_to_label[benchmark.code] = benchmark.label

        if selected_stock_ids:
            for stock_id, points in dto.stock_series.items():
                if points:
                    label = str(stock_id)
                    series_dict[label] = ComparisonSeriesBuilder._series_from_points(points, label)
                    code_to_label[str(stock_id)] = label

        return series_dict, code_to_label

    @staticmethod
    def build_override_series(
        dto,
        portfolio_code: str,
        asset_labels: dict[str, str],
    ) -> tuple[dict[str, pd.Series], dict[str, str]]:
        series_dict: dict[str, pd.Series] = {}
        code_to_label: dict[str, str] = {}

        if dto.portfolio_series:
            label = dto.current_portfolio_label
            series_dict[label] = ComparisonSeriesBuilder._series_from_points(dto.portfolio_series, label)
            code_to_label[portfolio_code] = label
            code_to_label[f"portfolio:{portfolio_code}"] = label

        for cp in dto.comparison_portfolios:
            if cp.points:
                series_dict[cp.label] = ComparisonSeriesBuilder._series_from_points(cp.points, cp.label)
                code_to_label[cp.code] = cp.label
                code_to_label[f"portfolio:{cp.code}"] = cp.label

        for stock_id, points in dto.stock_series.items():
            if points:
                label = asset_labels.get(str(stock_id), str(stock_id))
                series_dict[label] = ComparisonSeriesBuilder._series_from_points(points, label)

        return series_dict, code_to_label

    @staticmethod
    def _series_from_points(points, name: str) -> pd.Series:
        series = pd.Series({pd.Timestamp(d): float(v) for d, v in points.items()})
        series.name = name
        return series
