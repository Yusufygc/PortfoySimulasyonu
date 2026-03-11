# src/ui/pages/__init__.py
"""
Sayfa modülü - QStackedWidget ile kullanılan sayfa sınıfları.
"""

from .base_page import BasePage
from .dashboard_page import DashboardPage
from .watchlist_page import WatchlistPage
from .model_portfolio_page import ModelPortfolioPage
from .analysis_page import AnalysisPage
from .optimization_page import OptimizationPage
from .planning_page import PlanningPage
from .risk_profile_page import RiskProfilePage

__all__ = [
    "BasePage",
    "DashboardPage",
    "WatchlistPage",
    "ModelPortfolioPage",
    "AnalysisPage",
    "OptimizationPage",
    "PlanningPage",
    "RiskProfilePage",
]


