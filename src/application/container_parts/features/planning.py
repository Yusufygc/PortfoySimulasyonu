"""Planlama: izleme listesi, optimizasyon, bütçe/hedef, risk profili ve köprüsü."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.planning.optimization_service import OptimizationDeps, OptimizationService
from src.application.services.planning.planning_service import PlanningService
from src.application.services.planning.risk_optimization_bridge_service import RiskOptimizationBridgeService
from src.application.services.planning.risk_profile_service import RiskProfileService
from src.application.services.watchlist.watchlist_service import WatchlistService

PROVIDES = (
    "watchlist_service", "optimization_service", "planning_service", "risk_profile_service",
    "risk_optimization_bridge_service",
)


def build(ctx: BuildContext) -> dict:
    r, m, s = ctx.repositories, ctx.market_clients, ctx.services
    optimization = OptimizationService(deps=OptimizationDeps(
        portfolio_service=s["portfolio_service"], model_portfolio_service=s["model_portfolio_service"],
        stock_repo=r.stock_repo, market_data_provider=m.optimization_market_data_provider,
    ))
    risk_profile = RiskProfileService(risk_profile_repo=r.risk_profile_repo)
    return {
        "watchlist_service": WatchlistService(watchlist_repo=r.watchlist_repo, stock_repo=r.stock_repo),
        "optimization_service": optimization,
        "planning_service": PlanningService(planning_repo=r.planning_repo),
        "risk_profile_service": risk_profile,
        "risk_optimization_bridge_service": RiskOptimizationBridgeService(
            risk_profile_service=risk_profile, optimization_service=optimization,
        ),
    }
