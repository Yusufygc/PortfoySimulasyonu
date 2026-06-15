from __future__ import annotations

from dataclasses import dataclass

from src.application.container_parts.market_clients import MarketClientSet
from src.application.container_parts.repositories import RepositorySet
from src.application.services.analysis.analysis_service import AnalysisService, AnalysisServiceDeps
from src.application.services.analysis.financial_analysis_service import FinancialAnalysisService
from src.application.services.analysis.return_calc_service import ReturnCalcService
from src.application.services.corporate_actions.corporate_action_service import CorporateActionService
from src.application.services.corporate_actions.candidate_discovery_service import CandidateDiscoveryDeps, CorporateActionDiscoveryService
from src.application.services.corporate_actions.candidate_review_service import CorporateActionCandidateReviewService
from src.application.services.corporate_actions.price_adjustment_service import CorporateActionPriceAdjustmentService
from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.application.services.planning.optimization_service import OptimizationDeps, OptimizationService
from src.application.services.planning.planning_service import PlanningService
from src.application.services.planning.risk_profile_service import RiskProfileService
from src.application.services.portfolio.cash_movement_service import CashMovementService
from src.application.services.portfolio.portfolio_maintenance_service import PortfolioMaintenanceService
from src.application.services.portfolio.portfolio_reset_service import PortfolioResetService
from src.application.services.portfolio.portfolio_service import PortfolioService
from src.application.services.portfolio.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.application.services.portfolio.price_update_service import PriceUpdateService
from src.application.services.portfolio.trade_entry_service import TradeEntryService
from src.application.services.reporting.excel_export_service import ExcelExportService
from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.excel_report_builder import ExcelReportBuilder
from src.application.services.reporting.model_portfolio_excel_export_service import ModelPortfolioExcelExportService
from src.application.services.simulation.backfill_service import BackfillService
from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.application.services.simulation.model_portfolio_history_simulation_service import ModelPortfolioHistorySimulationService
from src.application.services.watchlist.watchlist_service import WatchlistService
from src.infrastructure.calendar.bist_holiday_provider import BistHolidayProvider
from src.infrastructure.corporate_actions import KapMkkCorporateActionProvider


@dataclass(frozen=True)
class ServiceSet:
    portfolio_service: PortfolioService
    cash_movement_service: CashMovementService
    portfolio_maintenance_service: PortfolioMaintenanceService
    trade_entry_service: TradeEntryService
    price_update_service: PriceUpdateService
    price_data_health_service: object
    live_price_refresh_service: object
    return_calc_service: ReturnCalcService
    model_portfolio_service: ModelPortfolioService
    analysis_service: AnalysisService
    reset_service: PortfolioResetService
    history_simulation_service: HistorySimulationService
    model_portfolio_history_simulation_service: ModelPortfolioHistorySimulationService
    excel_formatter: ExcelFormatter
    excel_report_builder: ExcelReportBuilder
    excel_export_service: ExcelExportService
    model_portfolio_excel_export_service: ModelPortfolioExcelExportService
    watchlist_service: WatchlistService
    optimization_service: OptimizationService
    planning_service: PlanningService
    risk_profile_service: RiskProfileService
    corporate_action_service: CorporateActionService
    corporate_action_discovery_service: CorporateActionDiscoveryService
    corporate_action_candidate_review_service: CorporateActionCandidateReviewService
    backfill_service: BackfillService
    update_coordinator: PortfolioUpdateCoordinator
    financial_analysis_service: FinancialAnalysisService


def build_services(repositories: RepositorySet, market_clients: MarketClientSet, event_bus) -> ServiceSet:
    foundation = _build_foundation_services(repositories, market_clients)
    reporting = _build_reporting_services(repositories, market_clients, foundation)
    feature_services = _build_feature_services(
        repositories,
        market_clients,
        foundation,
    )

    return ServiceSet(
        **foundation,
        **reporting,
        **feature_services,
        update_coordinator=PortfolioUpdateCoordinator(
            portfolio_repo=repositories.portfolio_repo,
            stock_repo=repositories.stock_repo,
            price_update_service=foundation["price_update_service"],
            return_calc_service=foundation["return_calc_service"],
            event_bus=event_bus,
        ),
        financial_analysis_service=FinancialAnalysisService(
            financial_statement_provider=market_clients.isyatirim_provider,
        ),
    )


def _build_foundation_services(repositories: RepositorySet, market_clients: MarketClientSet) -> dict:
    portfolio_service = PortfolioService(
        repositories.portfolio_repo,
        repositories.price_repo,
        cash_movement_repo=repositories.cash_movement_repo,
    )
    cash_movement_service = CashMovementService(
        cash_movement_repo=repositories.cash_movement_repo,
        portfolio_service=portfolio_service,
    )
    trade_entry_service = TradeEntryService(
        stock_repo=repositories.stock_repo,
        portfolio_service=portfolio_service,
        market_session_service=market_clients.bist_market_session_service,
    )
    price_update_service = PriceUpdateService(
        repositories.price_repo,
        market_clients.market_client,
        trading_calendar=market_clients.trading_calendar,
    )
    return_calc_service = ReturnCalcService(repositories.portfolio_repo, repositories.price_repo)
    model_portfolio_service = ModelPortfolioService(
        model_portfolio_repo=repositories.model_portfolio_repo,
        stock_repo=repositories.stock_repo,
        market_session_service=market_clients.bist_market_session_service,
    )

    return {
        "portfolio_service": portfolio_service,
        "cash_movement_service": cash_movement_service,
        "portfolio_maintenance_service": PortfolioMaintenanceService(
            maintenance_repo=repositories.portfolio_maintenance_repo,
        ),
        "trade_entry_service": trade_entry_service,
        "price_update_service": price_update_service,
        "return_calc_service": return_calc_service,
        "model_portfolio_service": model_portfolio_service,
    }


def _build_reporting_services(
    repositories: RepositorySet,
    market_clients: MarketClientSet,
    foundation: dict,
) -> dict:
    history_simulation_service = HistorySimulationService(
        portfolio_repo=repositories.portfolio_repo,
        price_repo=repositories.price_repo,
        stock_repo=repositories.stock_repo,
        trading_calendar=market_clients.trading_calendar,
    )
    model_portfolio_history_simulation_service = ModelPortfolioHistorySimulationService(
        model_portfolio_repo=repositories.model_portfolio_repo,
        price_repo=repositories.price_repo,
        stock_repo=repositories.stock_repo,
        trading_calendar=market_clients.trading_calendar,
    )
    excel_formatter = ExcelFormatter()
    excel_report_builder = ExcelReportBuilder(formatter=excel_formatter)

    return {
        "history_simulation_service": history_simulation_service,
        "model_portfolio_history_simulation_service": model_portfolio_history_simulation_service,
        "excel_formatter": excel_formatter,
        "excel_report_builder": excel_report_builder,
        "excel_export_service": ExcelExportService(
            simulation_service=history_simulation_service,
            report_builder=excel_report_builder,
        ),
        "model_portfolio_excel_export_service": ModelPortfolioExcelExportService(
            model_portfolio_service=foundation["model_portfolio_service"],
            stock_repo=repositories.stock_repo,
            formatter=excel_formatter,
            history_simulation_service=model_portfolio_history_simulation_service,
            report_builder=excel_report_builder,
        ),
    }


def _build_prereq_services(repositories: RepositorySet, market_clients: MarketClientSet):
    from src.application.services.market.price_data_health_service import PriceDataHealthService, PriceHealthServiceDeps
    corp_price_adj = CorporateActionPriceAdjustmentService(
        action_repo=repositories.corporate_action_repo,
        price_repo=repositories.price_repo,
    )
    corp_action = CorporateActionService(
        action_repo=repositories.corporate_action_repo,
        portfolio_repo=repositories.portfolio_repo,
        trade_adjustment_repo=getattr(repositories, "trade_adjustment_repo", None),
        price_adjustment_service=corp_price_adj,
    )
    health_service = PriceDataHealthService(
        deps=PriceHealthServiceDeps(
            stock_repo=repositories.stock_repo,
            price_repo=repositories.price_repo,
            market_data_client=market_clients.market_client,
            portfolio_repo=repositories.portfolio_repo,
            model_portfolio_repo=repositories.model_portfolio_repo,
            corporate_action_repo=repositories.corporate_action_repo,
        ),
        holiday_provider=BistHolidayProvider(),
    )
    return corp_action, health_service


def _build_market_services(repositories, market_clients, price_data_health_service, model_portfolio_service) -> dict:
    from src.application.services.market.live_price_refresh_service import LivePriceRefreshService
    return {
        "live_price_refresh_service": LivePriceRefreshService(
            stock_repo=repositories.stock_repo,
            price_lookup_service=market_clients.price_lookup_service,
            price_data_health_service=price_data_health_service,
            latest_price_repo=repositories.latest_price_repo,
        ),
        "analysis_service": AnalysisService(
            deps=AnalysisServiceDeps(
                portfolio_repo=repositories.portfolio_repo,
                price_repo=repositories.price_repo,
                stock_repo=repositories.stock_repo,
                market_data_client=market_clients.market_client,
            ),
            evds_client=market_clients.evds_client,
            cash_movement_repo=repositories.cash_movement_repo,
            model_portfolio_service=model_portfolio_service,
        ),
        "backfill_service": BackfillService(
            stock_repo=repositories.stock_repo,
            price_repo=repositories.price_repo,
            market_data_client=market_clients.market_client,
            corporate_action_repo=repositories.corporate_action_repo,
        ),
    }


def _build_portfolio_services(repositories, market_clients, foundation, model_portfolio_service) -> dict:
    return {
        "reset_service": PortfolioResetService(
            portfolio_repo=repositories.portfolio_repo,
            price_repo=repositories.price_repo,
            stock_repo=repositories.stock_repo,
            watchlist_repo=repositories.watchlist_repo,
            model_portfolio_repo=repositories.model_portfolio_repo,
            cash_movement_repo=repositories.cash_movement_repo,
        ),
        "watchlist_service": WatchlistService(
            watchlist_repo=repositories.watchlist_repo,
            stock_repo=repositories.stock_repo,
        ),
        "optimization_service": OptimizationService(
            deps=OptimizationDeps(
                portfolio_service=foundation["portfolio_service"],
                model_portfolio_service=model_portfolio_service,
                stock_repo=repositories.stock_repo,
                market_data_provider=market_clients.optimization_market_data_provider,
            ),
        ),
        "planning_service": PlanningService(planning_repo=repositories.planning_repo),
        "risk_profile_service": RiskProfileService(risk_profile_repo=repositories.risk_profile_repo),
    }


def _build_corporate_action_services(repositories, corp_action_service) -> dict:
    return {
        "corporate_action_discovery_service": CorporateActionDiscoveryService(
            deps=CandidateDiscoveryDeps(
                provider=KapMkkCorporateActionProvider(),
                candidate_repo=repositories.corporate_action_candidate_repo,
                stock_repo=repositories.stock_repo,
                action_repo=repositories.corporate_action_repo,
                portfolio_repo=repositories.portfolio_repo,
                watchlist_repo=repositories.watchlist_repo,
                model_portfolio_repo=repositories.model_portfolio_repo,
            ),
        ),
        "corporate_action_candidate_review_service": CorporateActionCandidateReviewService(
            candidate_repo=repositories.corporate_action_candidate_repo,
            corporate_action_service=corp_action_service,
        ),
    }


def _build_feature_services(
    repositories: RepositorySet,
    market_clients: MarketClientSet,
    foundation: dict,
) -> dict:
    model_portfolio_service = foundation["model_portfolio_service"]
    corp_action_service, price_data_health_service = _build_prereq_services(repositories, market_clients)
    return {
        "price_data_health_service": price_data_health_service,
        "corporate_action_service": corp_action_service,
        **_build_market_services(repositories, market_clients, price_data_health_service, model_portfolio_service),
        **_build_portfolio_services(repositories, market_clients, foundation, model_portfolio_service),
        **_build_corporate_action_services(repositories, corp_action_service),
    }
