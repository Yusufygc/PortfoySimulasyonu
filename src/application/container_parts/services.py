from __future__ import annotations

from dataclasses import dataclass

from src.application.container_parts.market_clients import MarketClientSet
from src.application.container_parts.repositories import RepositorySet
from src.application.services.analysis.analysis_service import AnalysisService, AnalysisServiceDeps
from src.application.services.assets.asset_chart_service import AssetChartService
from src.application.services.assets.asset_holdings_reader import AssetHoldingsReader
from src.application.services.assets.asset_ledger_service import AssetLedgerService
from src.application.services.assets.asset_price_refresh_service import AssetPriceRefreshService
from src.application.services.assets.bist_holdings_reader import BistHoldingsReader
from src.application.services.assets.fx_rate_service import FxRateService
from src.application.services.assets.unified_portfolio_service import UnifiedPortfolioService
from src.application.services.portfolio.position_query_service import PositionQueryService
from src.application.services.portfolio.cash_pool_service import CashPoolService
from src.application.services.portfolio.fx_conversion_service import FxConversionService
from src.application.services.portfolio.pooled_cash_movement_repository import PooledCashMovementRepository
from src.application.services.settings.fee_settings_service import FeeSettingsService
from src.application.services.news.news_service import NewsService
from src.application.services.news.news_target_service import NewsTargetService
from src.application.services.analysis.financial_analysis_service import FinancialAnalysisService
from src.application.services.analysis.portfolio_analytics_service import PortfolioAnalyticsService
from src.application.services.analysis.shareholder_analysis_service import ShareholderAnalysisService
from src.application.services.analysis.stock_360_service import Stock360Service
from src.application.services.analysis.technical.technical_analysis_service import TechnicalAnalysisService
from src.application.services.analysis.technical.screener_service import ScreenerService
from src.application.services.analysis.return_calc_service import ReturnCalcService
from src.application.services.corporate_actions.corporate_action_service import CorporateActionService
from src.application.services.market.current_price_resolver import CurrentPriceResolver
from src.application.services.market.stock_lookup_service import StockLookupService
from src.application.services.market.market_indicators_service import MarketIndicatorsService
from src.application.services.market_data.market_data_sync_service import MarketDataSyncService
from src.application.services.corporate_actions.candidate_discovery_service import CandidateDiscoveryDeps, CorporateActionDiscoveryService
from src.application.services.corporate_actions.candidate_review_service import CorporateActionCandidateReviewService
from src.application.services.corporate_actions.market_action_service import MarketCorporateActionService
from src.application.services.corporate_actions.price_adjustment_service import CorporateActionPriceAdjustmentService
from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.application.services.planning.optimization_service import OptimizationDeps, OptimizationService
from src.application.services.planning.planning_service import PlanningService
from src.application.services.planning.risk_optimization_bridge_service import RiskOptimizationBridgeService
from src.application.services.planning.risk_profile_service import RiskProfileService
from src.application.services.portfolio.cash_movement_service import CashMovementService
from src.application.services.portfolio.portfolio_maintenance_service import PortfolioMaintenanceService
from src.application.services.portfolio.portfolio_reset_service import PortfolioResetService
from src.application.services.portfolio.portfolio_service import PortfolioService
from src.application.services.portfolio.trade_entry_service import TradeEntryService
from src.application.services.reporting.excel_export_service import ExcelExportService
from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.excel_report_builder import ExcelReportBuilder
from src.application.services.reporting.model_portfolio_excel_export_service import ModelPortfolioExcelExportService
from src.application.services.simulation.backfill_service import BackfillService
from src.application.services.simulation.dca_backtest_service import DCABacktestService
from src.application.services.simulation.strategy_backtest_service import StrategyBacktestService
from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.application.services.simulation.model_portfolio_history_simulation_service import ModelPortfolioHistorySimulationService
from src.application.services.watchlist.watchlist_service import WatchlistService
from src.infrastructure.calendar.bist_holiday_provider import BistHolidayProvider
from src.infrastructure.corporate_actions import KapMkkCorporateActionProvider
from src.infrastructure.news.default_sources import default_news_sources
from src.infrastructure.news.news_file_cache import JsonFileNewsCache
from src.infrastructure.news.provider_factory import NewsProviderFactory



@dataclass(frozen=True)
class ServiceSet:
    portfolio_service: PortfolioService
    cash_movement_service: CashMovementService
    portfolio_maintenance_service: PortfolioMaintenanceService
    trade_entry_service: TradeEntryService
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
    financial_analysis_service: FinancialAnalysisService
    shareholder_analysis_service: ShareholderAnalysisService
    stock_360_service: Stock360Service
    portfolio_analytics_service: PortfolioAnalyticsService
    risk_optimization_bridge_service: RiskOptimizationBridgeService
    technical_analysis_service: TechnicalAnalysisService
    screener_service: ScreenerService
    dca_backtest_service: DCABacktestService
    strategy_backtest_service: StrategyBacktestService
    current_price_resolver: object  # CurrentPriceResolver
    stock_lookup_service: StockLookupService  # arayüz için salt okunur hisse/fiyat sorguları
    market_data_sync_service: object  # MarketDataSyncService (DuckDB + SQLite köprüsü)
    market_corporate_action_service: MarketCorporateActionService  # DuckDB ticker bazlı sermaye artırımı
    market_indicators_service: object  # MarketIndicatorsService | None (üst piyasa şeridi)
    asset_ledger_service: AssetLedgerService  # BIST dışı varlık defteri (Portföyüm)
    asset_price_refresh_service: AssetPriceRefreshService  # varlık son fiyat ve geçmiş yenileme
    fx_rate_service: FxRateService  # kur okuma ve yenileme
    unified_portfolio_service: UnifiedPortfolioService  # BIST + varlık defteri birleşik TRY özeti
    pooled_cash_repo: PooledCashMovementRepository  # TL nakit görünümü (gerçek hareketler + havuz çıkış/girişleri)
    cash_pool_service: CashPoolService  # ortak nakit havuzu bakiyeleri (TL ve USD)
    fx_conversion_service: FxConversionService  # TL <-> USD döviz al/sat
    fee_settings_service: FeeSettingsService  # komisyon ve BSMV oranları (varsayılan 0) ve ücret hesabı
    position_query_service: PositionQueryService  # pozisyon rakamlarının tek okuma kaynağı (Portföyüm ile aynı değerleme)
    asset_chart_service: AssetChartService  # Genel Bakış grafiği için varlık fiyat serileri
    news_service: NewsService  # haber akışı (KAP, RSS, Yahoo, Google)
    news_target_service: NewsTargetService  # haber sorgusu yapılacak takip hedefleri


def _build_analysis_services(repositories, market_clients, feature_services: dict) -> dict:
    financial_analysis_service = FinancialAnalysisService(
        financial_statement_provider=market_clients.isyatirim_provider,
        inflation_provider=market_clients.evds_tufe_provider,
        valuation_provider=market_clients.yfinance_valuation_provider,
    )
    shareholder_analysis_service = ShareholderAnalysisService(
        provider=market_clients.kap_shareholder_provider,
        repository=repositories.kap_shareholder_repo,
    )
    return {
        "financial_analysis_service": financial_analysis_service,
        "shareholder_analysis_service": shareholder_analysis_service,
        "stock_360_service": Stock360Service(
            price_repo=repositories.price_repo,
            stock_repo=repositories.stock_repo,
            financial_analysis_service=financial_analysis_service,
            shareholder_analysis_service=shareholder_analysis_service,
            market_history_repo=repositories.market_history_repo,
        ),
        "portfolio_analytics_service": PortfolioAnalyticsService(analysis_service=feature_services["analysis_service"]),
        "risk_optimization_bridge_service": RiskOptimizationBridgeService(
            risk_profile_service=feature_services["risk_profile_service"],
            optimization_service=feature_services["optimization_service"],
        ),
        "technical_analysis_service": TechnicalAnalysisService(
            market_history_repo=repositories.market_history_repo,
            golden_cross_repo=repositories.golden_cross_repo,
        ),
        "screener_service": ScreenerService(market_history_repo=repositories.market_history_repo),
        "dca_backtest_service": DCABacktestService(
            price_repo=repositories.price_repo,
            stock_repo=repositories.stock_repo,
            market_history_repo=repositories.market_history_repo,
        ),
        "strategy_backtest_service": StrategyBacktestService(
            price_repo=repositories.price_repo,
            stock_repo=repositories.stock_repo,
            market_history_repo=repositories.market_history_repo,
        ),
    }


def build_services(repositories: RepositorySet, market_clients: MarketClientSet) -> ServiceSet:
    foundation = _build_foundation_services(repositories, market_clients)
    reporting = _build_reporting_services(repositories, market_clients, foundation)
    feature_services = _build_feature_services(
        repositories,
        market_clients,
        foundation,
    )

    analysis = _build_analysis_services(repositories, market_clients, feature_services)

    current_price_resolver = CurrentPriceResolver(
        latest_price_repo=repositories.latest_price_repo,
        price_repo=repositories.price_repo,
        session_service=market_clients.bist_market_session_service,
    )
    stock_lookup_service = StockLookupService(
        stock_repo=repositories.stock_repo,
        price_repo=repositories.price_repo,
        latest_price_repo=repositories.latest_price_repo,
        market_history_repo=repositories.market_history_repo,
        price_lookup_service=market_clients.price_lookup_service,
    )
    asset_ledger_service = AssetLedgerService(
        asset_repo=repositories.asset_repo,
        trade_repo=repositories.asset_trade_repo,
        symbol_verifier=market_clients.asset_price_provider,
        fee_service=foundation["fee_settings_service"],
        cash_pool=foundation["cash_pool_service"],
    )
    fx_rate_service = FxRateService(
        provider=market_clients.asset_price_provider,
        repo=repositories.fx_rate_repo,
    )
    bist_holdings_reader = BistHoldingsReader(foundation["portfolio_service"], stock_lookup_service, current_price_resolver)
    fx_conversion_service = FxConversionService(
        repositories.fx_conversion_repo, foundation["cash_pool_service"], fx_rate_service
    )
    unified_portfolio_service = UnifiedPortfolioService(
        bist_reader=bist_holdings_reader,
        asset_reader=AssetHoldingsReader(asset_ledger_service, repositories.asset_price_repo, fx_rate_service),
        fx_rate_service=fx_rate_service,
    )

    return ServiceSet(
        **foundation,
        **reporting,
        **feature_services,
        **analysis,
        current_price_resolver=current_price_resolver,
        stock_lookup_service=stock_lookup_service,
        market_indicators_service=(
            MarketIndicatorsService(market_clients.market_indicator_provider)
            if getattr(market_clients, "market_indicator_provider", None) is not None
            else None
        ),
        asset_ledger_service=asset_ledger_service,
        asset_price_refresh_service=AssetPriceRefreshService(
            asset_repo=repositories.asset_repo,
            price_repo=repositories.asset_price_repo,
            provider=market_clients.asset_price_provider,
        ),
        fx_rate_service=fx_rate_service,
        unified_portfolio_service=unified_portfolio_service,
        fx_conversion_service=fx_conversion_service,
        position_query_service=PositionQueryService(
            bist_reader=bist_holdings_reader,
            model_portfolio_service=foundation["model_portfolio_service"],
            stock_lookup_service=stock_lookup_service,
            price_resolver=current_price_resolver,
        ),
        asset_chart_service=AssetChartService(asset_ledger_service, repositories.asset_price_repo),
        news_service=NewsService(
            source_repo=repositories.news_source_repo,
            provider_factory=NewsProviderFactory(lambda ticker: market_clients.kap_shareholder_provider.resolve_member_oid(ticker)[0]),
            cache=JsonFileNewsCache(),
            default_sources=default_news_sources,
        ),
        news_target_service=NewsTargetService(
            portfolio_service=foundation["portfolio_service"],
            stock_lookup_service=stock_lookup_service,
            asset_ledger_service=asset_ledger_service,
            watchlist_service=feature_services["watchlist_service"],
        ),
        market_data_sync_service=MarketDataSyncService(
            repositories.market_history_store,
            getattr(market_clients, "market_bar_downloader", None),
            trading_calendar=market_clients.trading_calendar,
            price_repo=repositories.price_repo,
            stock_repo=repositories.stock_repo,
            market_action_service=feature_services["market_corporate_action_service"],
            portfolio_action_repo=repositories.corporate_action_repo,
        ),
    )


def _build_foundation_services(repositories: RepositorySet, market_clients: MarketClientSet) -> dict:
    # TL nakit görünümü: gerçek hareketler + ortak havuzdan TL çıkış/girişleri (döviz çevirme, TL ile ödenen varlık)
    pooled_cash_repo = PooledCashMovementRepository(
        repositories.cash_movement_repo, repositories.fx_conversion_repo,
        repositories.asset_trade_repo, repositories.asset_repo,
    )
    portfolio_service = PortfolioService(
        repositories.portfolio_repo,
        repositories.price_repo,
        cash_movement_repo=pooled_cash_repo,
    )
    cash_pool_service = CashPoolService(
        portfolio_service, repositories.fx_conversion_repo, repositories.asset_trade_repo, repositories.asset_repo
    )
    fee_settings_service = FeeSettingsService(repositories.app_settings_repo)
    cash_movement_service = CashMovementService(
        cash_movement_repo=pooled_cash_repo,
        portfolio_service=portfolio_service,
    )
    trade_entry_service = TradeEntryService(
        stock_repo=repositories.stock_repo,
        portfolio_service=portfolio_service,
        market_session_service=market_clients.bist_market_session_service,
        fee_service=fee_settings_service,
    )
    return_calc_service = ReturnCalcService(repositories.portfolio_repo, repositories.price_repo)
    model_portfolio_service = ModelPortfolioService(
        model_portfolio_repo=repositories.model_portfolio_repo,
        stock_repo=repositories.stock_repo,
        market_session_service=market_clients.bist_market_session_service,
    )

    return {
        "pooled_cash_repo": pooled_cash_repo,
        "cash_pool_service": cash_pool_service,
        "fee_settings_service": fee_settings_service,
        "portfolio_service": portfolio_service,
        "cash_movement_service": cash_movement_service,
        "portfolio_maintenance_service": PortfolioMaintenanceService(
            maintenance_repo=repositories.portfolio_maintenance_repo,
        ),
        "trade_entry_service": trade_entry_service,
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
    market_action_service = MarketCorporateActionService(
        history_repo=repositories.market_history_repo,
        action_repo=repositories.market_action_repo,
    )
    corp_price_adj = CorporateActionPriceAdjustmentService(
        action_repo=repositories.corporate_action_repo,
        price_repo=repositories.price_repo,
        stock_repo=repositories.stock_repo,
        market_action_service=market_action_service,
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
    return corp_action, health_service, market_action_service


def _watchlist_stock_ids(watchlist_repo) -> set:
    """Tüm izleme listelerindeki hisse kimlikleri (canlı fiyat yenilemesine dahil edilir)."""
    return {
        item.stock_id
        for watchlist in watchlist_repo.get_all_watchlists()
        for item in watchlist_repo.get_items_by_watchlist_id(watchlist.id)
    }


def _build_market_services(repositories, market_clients, price_data_health_service, model_portfolio_service, cash_movement_repo) -> dict:
    from src.application.services.market.live_price_refresh_service import LivePriceRefreshService
    return {
        "live_price_refresh_service": LivePriceRefreshService(
            stock_repo=repositories.stock_repo,
            price_lookup_service=market_clients.price_lookup_service,
            price_data_health_service=price_data_health_service,
            latest_price_repo=repositories.latest_price_repo,
            extra_stock_ids_provider=lambda: _watchlist_stock_ids(repositories.watchlist_repo),
        ),
        "analysis_service": AnalysisService(
            deps=AnalysisServiceDeps(
                portfolio_repo=repositories.portfolio_repo,
                price_repo=repositories.price_repo,
                stock_repo=repositories.stock_repo,
                market_data_client=market_clients.market_client,
            ),
            evds_client=market_clients.evds_client,
            cash_movement_repo=cash_movement_repo,
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
            asset_repo=repositories.asset_repo,
            fx_conversion_repo=repositories.fx_conversion_repo,
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
    corp_action_service, price_data_health_service, market_action_service = _build_prereq_services(
        repositories, market_clients
    )
    return {
        "price_data_health_service": price_data_health_service,
        "corporate_action_service": corp_action_service,
        "market_corporate_action_service": market_action_service,
        **_build_market_services(
            repositories, market_clients, price_data_health_service, model_portfolio_service, foundation["pooled_cash_repo"]
        ),
        **_build_portfolio_services(repositories, market_clients, foundation, model_portfolio_service),
        **_build_corporate_action_services(repositories, corp_action_service),
    }
