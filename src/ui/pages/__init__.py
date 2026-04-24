# src/ui/pages/__init__.py
"""
Sayfa modülü - QStackedWidget ile kullanılan sayfa sınıfları.
"""

from .base_page import BasePage
from .dashboard import DashboardPage
from .watchlist_page import WatchlistPage
from .model_portfolio_page import ModelPortfolioPage
from .analysis import AnalysisPage
from .optimization_page import OptimizationPage
from .planning_page import PlanningPage
from .risk_profile_page import RiskProfilePage
from .settings_page import SettingsPage

__all__ = [
    "BasePage",
    "DashboardPage",
    "WatchlistPage",
    "ModelPortfolioPage",
    "AnalysisPage",
    "OptimizationPage",
    "PlanningPage",
    "RiskProfilePage",
    "SettingsPage",
]


