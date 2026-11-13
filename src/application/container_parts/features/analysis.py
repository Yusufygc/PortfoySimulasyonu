"""Analiz: karşılaştırma ve risk, mali tablolar, ortaklık yapısı, Hisse 360, teknik analiz ve tarayıcı, backtest."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.analysis.analysis_service import AnalysisService, AnalysisServiceDeps
from src.application.services.analysis.financial_analysis_service import FinancialAnalysisService
from src.application.services.analysis.portfolio_analytics_service import PortfolioAnalyticsService
from src.application.services.analysis.shareholder_analysis_service import ShareholderAnalysisService
from src.application.services.analysis.stock_360_service import Stock360Service
from src.application.services.analysis.technical.screener_service import ScreenerService
from src.application.services.analysis.technical.technical_analysis_service import TechnicalAnalysisService
from src.application.services.analysis.unified_series_builder import UnifiedSeriesBuilder, UnifiedSeriesDeps
from src.application.services.simulation.dca_backtest_service import DCABacktestService
from src.application.services.simulation.strategy_backtest_service import StrategyBacktestService

PROVIDES = (
    "analysis_service", "financial_analysis_service", "shareholder_analysis_service", "stock_360_service",
    "portfolio_analytics_service", "technical_analysis_service", "screener_service", "dca_backtest_service",
    "strategy_backtest_service",
)


def unified_series_builder(r) -> UnifiedSeriesBuilder:
    """Birleşik analiz serisi: GERÇEK nakit hareketleri (havuz görünümü değil) ve varlık/döviz defterleri."""
    return UnifiedSeriesBuilder(UnifiedSeriesDeps(
        portfolio_repo=r.portfolio_repo, price_repo=r.price_repo, stock_repo=r.stock_repo,
        cash_repo=r.cash_movement_repo, asset_repo=r.asset_repo, asset_trade_repo=r.asset_trade_repo,
        asset_price_repo=r.asset_price_repo, fx_rate_repo=r.fx_rate_repo, fx_conversion_repo=r.fx_conversion_repo,
    ))


def _analysis_service(ctx: BuildContext) -> AnalysisService:
    r, m, s = ctx.repositories, ctx.market_clients, ctx.services
    fallback = ctx.market_settings.tcmb_deposit_rate_fallback if ctx.market_settings else None
    return AnalysisService(
        deps=AnalysisServiceDeps(
            portfolio_repo=r.portfolio_repo, price_repo=r.price_repo, stock_repo=r.stock_repo,
            market_data_client=m.market_client, deposit_rate_fallback=fallback,
        ),
        evds_client=m.evds_client, cash_movement_repo=s["pooled_cash_repo"],
        model_portfolio_service=s["model_portfolio_service"], unified_builder=unified_series_builder(r),
    )


def build(ctx: BuildContext) -> dict:
    r, m = ctx.repositories, ctx.market_clients
    analysis_service = _analysis_service(ctx)
    financial = FinancialAnalysisService(
        financial_statement_provider=m.isyatirim_provider, inflation_provider=m.evds_tufe_provider,
        valuation_provider=m.yfinance_valuation_provider,
    )
    shareholder = ShareholderAnalysisService(provider=m.kap_shareholder_provider, repository=r.kap_shareholder_repo)
    history = dict(price_repo=r.price_repo, stock_repo=r.stock_repo, market_history_repo=r.market_history_repo)
    return {
        "analysis_service": analysis_service,
        "financial_analysis_service": financial,
        "shareholder_analysis_service": shareholder,
        "stock_360_service": Stock360Service(
            financial_analysis_service=financial, shareholder_analysis_service=shareholder, **history,
        ),
        "portfolio_analytics_service": PortfolioAnalyticsService(analysis_service=analysis_service),
        "technical_analysis_service": TechnicalAnalysisService(
            market_history_repo=r.market_history_repo, golden_cross_repo=r.golden_cross_repo,
        ),
        "screener_service": ScreenerService(market_history_repo=r.market_history_repo),
        "dca_backtest_service": DCABacktestService(**history),
        "strategy_backtest_service": StrategyBacktestService(**history),
    }
