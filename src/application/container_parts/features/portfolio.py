"""Ana portföy, nakit havuzu, ücretler, işlem girişi, model portföy, sıfırlama."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.analysis.return_calc_service import ReturnCalcService
from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.application.services.portfolio.cash_movement_service import CashMovementService
from src.application.services.portfolio.cash_pool_service import CashPoolService
from src.application.services.portfolio.pooled_cash_movement_repository import PooledCashMovementRepository
from src.application.services.portfolio.portfolio_maintenance_service import PortfolioMaintenanceService
from src.application.services.portfolio.portfolio_reset_service import PortfolioResetService
from src.application.services.portfolio.portfolio_service import PortfolioService
from src.application.services.portfolio.trade_entry_service import TradeEntryService
from src.application.services.settings.fee_settings_service import FeeSettingsService

PROVIDES = (
    "pooled_cash_repo", "cash_pool_service", "fee_settings_service", "portfolio_service", "cash_movement_service",
    "portfolio_maintenance_service", "trade_entry_service", "return_calc_service", "model_portfolio_service",
    "reset_service",
)


def build(ctx: BuildContext) -> dict:
    r, m = ctx.repositories, ctx.market_clients
    # TL nakit görünümü: gerçek hareketler + ortak havuzdan TL çıkış/girişleri (döviz çevirme, TL ile ödenen varlık)
    pooled_cash_repo = PooledCashMovementRepository(r.cash_movement_repo, r.fx_conversion_repo, r.asset_trade_repo, r.asset_repo)
    portfolio_service = PortfolioService(r.portfolio_repo, r.price_repo, cash_movement_repo=pooled_cash_repo)
    fee_settings_service = FeeSettingsService(r.app_settings_repo)
    return {
        "pooled_cash_repo": pooled_cash_repo,
        "cash_pool_service": CashPoolService(portfolio_service, r.fx_conversion_repo, r.asset_trade_repo, r.asset_repo),
        "fee_settings_service": fee_settings_service,
        "portfolio_service": portfolio_service,
        "cash_movement_service": CashMovementService(cash_movement_repo=pooled_cash_repo, portfolio_service=portfolio_service),
        "portfolio_maintenance_service": PortfolioMaintenanceService(maintenance_repo=r.portfolio_maintenance_repo),
        "trade_entry_service": TradeEntryService(
            stock_repo=r.stock_repo, portfolio_service=portfolio_service,
            market_session_service=m.bist_market_session_service, fee_service=fee_settings_service,
        ),
        "return_calc_service": ReturnCalcService(r.portfolio_repo, r.price_repo),
        "model_portfolio_service": ModelPortfolioService(
            model_portfolio_repo=r.model_portfolio_repo, stock_repo=r.stock_repo,
            market_session_service=m.bist_market_session_service,
        ),
        "reset_service": PortfolioResetService(
            portfolio_repo=r.portfolio_repo, price_repo=r.price_repo, stock_repo=r.stock_repo,
            watchlist_repo=r.watchlist_repo, model_portfolio_repo=r.model_portfolio_repo,
            cash_movement_repo=r.cash_movement_repo, asset_repo=r.asset_repo, fx_conversion_repo=r.fx_conversion_repo,
        ),
    }
