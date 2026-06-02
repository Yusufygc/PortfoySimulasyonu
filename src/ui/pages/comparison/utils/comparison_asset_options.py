from __future__ import annotations

from collections.abc import Callable


class ComparisonAssetOptions:
    """Manage selectable assets and per-chart portfolio override choices."""

    def __init__(self, page, analysis_service, override_callback: Callable[[str, str | None], None]) -> None:
        self.page = page
        self.analysis_service = analysis_service
        self.override_callback = override_callback

    def get_current_base_assets(self) -> list[tuple[str, str]]:
        assets: list[tuple[str, str]] = []
        page = self.page

        if not hasattr(page, "_asset_labels"):
            page._asset_labels = {}

        portfolios = self.analysis_service.get_portfolio_options()
        for portfolio in portfolios:
            assets.append((portfolio.label, portfolio.code))
            assets.append((f"{portfolio.label} + Hisseleri", f"holdings:{portfolio.code}"))
            page._asset_labels[portfolio.code] = portfolio.label
            page._asset_labels[f"holdings:{portfolio.code}"] = f"{portfolio.label} + Hisseleri"

        benchmarks = self.analysis_service.get_benchmark_definitions()
        for benchmark in benchmarks:
            assets.append((benchmark.label, benchmark.code))
            page._asset_labels[benchmark.code] = benchmark.label

        for code, label in page._asset_labels.items():
            if code.isdigit() and not any(item[1] == code for item in assets):
                assets.append((label, code))

        page._base_assets_cache = assets
        return assets

    def load_initial_options(self) -> None:
        page = self.page
        page._asset_labels = {}
        assets = self.get_current_base_assets()
        page.ribbon_bar.set_assets(assets)
        self.refresh_panel_options()

    def refresh_panel_options(self) -> None:
        page = self.page
        portfolio_choices = [
            (portfolio.label, portfolio.code)
            for portfolio in self.analysis_service.get_portfolio_options()
        ]
        panel_keys = [
            ("main_chart_panel", "main_chart"),
            ("summary_table_panel", "summary_table"),
            ("drawdown_chart_panel", "drawdown_chart"),
            ("periodic_chart_panel", "periodic_chart"),
            ("scatter_chart_panel", "scatter_chart"),
            ("treemap_chart_panel", "treemap_chart"),
        ]
        for panel_attr, chart_key in panel_keys:
            panel = getattr(page, panel_attr, None)
            if panel is None:
                continue
            panel.update_portfolio_options(
                portfolio_choices,
                page.chart_overrides.get(chart_key),
                lambda code, ck=chart_key: self.override_callback(ck, code),
            )
