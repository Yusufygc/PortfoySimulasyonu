from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PurgeStockResult:
    ticker: str
    stock_ids: tuple[int, ...]
    deleted_trades: int = 0
    deleted_daily_prices: int = 0
    deleted_watchlist_items: int = 0
    deleted_model_portfolio_trades: int = 0
    deleted_corporate_actions: int = 0
    deleted_stocks: int = 0


class PortfolioMaintenanceService:
    def __init__(self, maintenance_repo) -> None:
        self._maintenance_repo = maintenance_repo

    def purge_stock_by_ticker(self, ticker: str) -> PurgeStockResult:
        normalized = self._normalize_ticker(ticker)
        return self._maintenance_repo.purge_stock_by_ticker(normalized)

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        value = (ticker or "").strip().upper()
        if not value:
            raise ValueError("Silinecek hisse kodu bos olamaz.")
        return value[:-3] if value.endswith(".IS") else value
