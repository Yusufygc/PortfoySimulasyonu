from __future__ import annotations


class PageFactory:
    def __init__(self, container, price_lookup_func, parent_window) -> None:
        self._container = container
        self._price_lookup_func = price_lookup_func
        self._parent_window = parent_window
        self._builders = {
            0: self._create_dashboard,
            1: self._create_watchlist,
            2: self._create_model_portfolio,
            3: self._create_analysis,
            4: self._create_stock_detail,
            5: self._create_optimization,
            6: self._create_planning,
            7: self._create_risk_profile,
            8: self._create_ai_page,
            9: self._create_settings,
        }

    def create(self, page_index: int):
        builder = self._builders.get(page_index)
        if builder is None:
            return None
        return builder()

    def _create_dashboard(self):
        from src.ui.pages.dashboard import DashboardPage

        return DashboardPage(container=self._container, price_lookup_func=self._price_lookup_func)

    def _create_watchlist(self):
        from src.ui.pages.watchlist_page import WatchlistPage

        return WatchlistPage(container=self._container)

    def _create_model_portfolio(self):
        from src.ui.pages.model_portfolio_page import ModelPortfolioPage

        return ModelPortfolioPage(container=self._container, price_lookup_func=self._price_lookup_func)

    def _create_analysis(self):
        from src.ui.pages.analysis import AnalysisPage

        return AnalysisPage(container=self._container)

    def _create_stock_detail(self):
        from src.ui.pages.stock_detail import StockDetailPage

        return StockDetailPage(
            container=self._container,
            price_lookup_func=self._price_lookup_func,
            parent=self._parent_window,
        )

    def _create_optimization(self):
        from src.ui.pages.optimization_page import OptimizationPage

        return OptimizationPage(container=self._container, price_lookup_func=self._price_lookup_func)

    def _create_planning(self):
        from src.ui.pages.planning_page import PlanningPage

        return PlanningPage(container=self._container)

    def _create_risk_profile(self):
        from src.ui.pages.risk_profile_page import RiskProfilePage

        return RiskProfilePage(container=self._container)

    def _create_ai_page(self):
        from src.ui.pages.ai_page import AIPage

        return AIPage(container=self._container)

    def _create_settings(self):
        from src.ui.pages.settings_page import SettingsPage

        return SettingsPage(container=self._container)
