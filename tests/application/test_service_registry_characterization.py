"""Servis kaydı karakterizasyonu: özellik başına kayda geçişten önce/sonra aynı servis adları ve tipleri."""
import dataclasses

from test_container_services import _fake_market_clients, _fake_repositories

from src.application.container_parts.services import build_services

EXPECTED = {
    'portfolio_service': 'PortfolioService', 'cash_movement_service': 'CashMovementService',
    'portfolio_maintenance_service': 'PortfolioMaintenanceService', 'trade_entry_service': 'TradeEntryService',
    'price_data_health_service': 'PriceDataHealthService', 'live_price_refresh_service': 'LivePriceRefreshService',
    'return_calc_service': 'ReturnCalcService', 'model_portfolio_service': 'ModelPortfolioService',
    'analysis_service': 'AnalysisService', 'reset_service': 'PortfolioResetService',
    'history_simulation_service': 'HistorySimulationService',
    'model_portfolio_history_simulation_service': 'ModelPortfolioHistorySimulationService',
    'excel_formatter': 'ExcelFormatter', 'excel_report_builder': 'ExcelReportBuilder',
    'excel_export_service': 'ExcelExportService', 'model_portfolio_excel_export_service': 'ModelPortfolioExcelExportService',
    'watchlist_service': 'WatchlistService', 'optimization_service': 'OptimizationService',
    'planning_service': 'PlanningService', 'risk_profile_service': 'RiskProfileService',
    'corporate_action_service': 'CorporateActionService',
    'corporate_action_discovery_service': 'CorporateActionDiscoveryService',
    'split_automation_service': 'SplitAutomationService',
    'corporate_action_candidate_review_service': 'CorporateActionCandidateReviewService',
    'backfill_service': 'BackfillService', 'financial_analysis_service': 'FinancialAnalysisService',
    'shareholder_analysis_service': 'ShareholderAnalysisService', 'stock_360_service': 'Stock360Service',
    'portfolio_analytics_service': 'PortfolioAnalyticsService',
    'risk_optimization_bridge_service': 'RiskOptimizationBridgeService',
    'technical_analysis_service': 'TechnicalAnalysisService', 'screener_service': 'ScreenerService',
    'dca_backtest_service': 'DCABacktestService', 'strategy_backtest_service': 'StrategyBacktestService',
    'current_price_resolver': 'CurrentPriceResolver', 'stock_lookup_service': 'StockLookupService',
    'market_data_sync_service': 'MarketDataSyncService', 'market_corporate_action_service': 'MarketCorporateActionService',
    'market_indicators_service': 'NoneType', 'asset_ledger_service': 'AssetLedgerService',
    'asset_price_refresh_service': 'AssetPriceRefreshService', 'fx_rate_service': 'FxRateService',
    'unified_portfolio_service': 'UnifiedPortfolioService', 'unified_optimization_service': 'UnifiedOptimizationService',
    'unified_return_service': 'UnifiedReturnService', 'pooled_cash_repo': 'PooledCashMovementRepository',
    'cash_pool_service': 'CashPoolService', 'fx_conversion_service': 'FxConversionService',
    'fee_settings_service': 'FeeSettingsService', 'position_query_service': 'PositionQueryService',
    'asset_chart_service': 'AssetChartService', 'news_service': 'NewsService', 'news_target_service': 'NewsTargetService',
    'price_projection_service': 'PriceProjectionService',  # B2: tek fiyat kaynağı
    'market_price_refresher': 'MarketPriceRefresher',
}


def _service_map(services) -> dict:
    if dataclasses.is_dataclass(services):
        items = {f.name: getattr(services, f.name) for f in dataclasses.fields(services)}
    else:
        items = dict(services.items())
    return {name: type(value).__name__ for name, value in items.items()}


def test_service_names_and_types_are_unchanged():
    services = build_services(repositories=_fake_repositories(), market_clients=_fake_market_clients())
    assert _service_map(services) == EXPECTED


def test_shared_instances_are_shared():
    """Aynı nesneyi kullanması gereken servisler (tek uygulayıcı, tek portföy servisi) aynı örneği görür."""
    s = build_services(repositories=_fake_repositories(), market_clients=_fake_market_clients())
    assert s.split_automation_service._d.applier is s.corporate_action_service._split_applier._applier
    assert s.cash_movement_service._portfolio_service is s.portfolio_service
    assert s.risk_optimization_bridge_service._optimization_service is s.optimization_service


def test_registry_rejects_unknown_names_and_writes():
    import pytest

    from src.application.container_parts.features import ServiceRegistry

    registry = ServiceRegistry({"a_service": 1})
    assert registry.a_service == 1 and "a_service" in registry and registry.names() == ("a_service",)
    with pytest.raises(AttributeError):
        registry.missing_service
    with pytest.raises(AttributeError):
        registry.a_service = 2


def test_feature_must_build_exactly_what_it_provides():
    import types

    import pytest

    from src.application.container_parts.features import BuildContext, build_features

    def feature(name, provides, built):
        module = types.ModuleType(f"features.{name}")
        module.PROVIDES, module.build = provides, lambda ctx: dict(built)
        return module

    with pytest.raises(RuntimeError, match="PROVIDES"):
        build_features(BuildContext(None, None), [feature("x", ("a",), {"a": 1, "b": 2})])
    with pytest.raises(RuntimeError, match="başka özellikte"):
        build_features(BuildContext(None, None), [feature("x", ("a",), {"a": 1}), feature("y", ("a",), {"a": 2})])


def test_static_service_names_match_built_services():
    from src.application.container_parts import service_names

    services = build_services(repositories=_fake_repositories(), market_clients=_fake_market_clients())
    assert sorted(service_names()) == sorted(services.names()) == sorted(EXPECTED)
