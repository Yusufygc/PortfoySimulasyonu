from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.application.services.reporting.daily_history_models import DailyPortfolioSnapshot, PortfolioStatus


@dataclass
class SnapshotBuildResult:
    snapshot: DailyPortfolioSnapshot
    base_portfolio_value: Decimal | None
    last_portfolio_value: Decimal | None


class HistorySnapshotBuilder:
    def build(
        self,
        current_date: date,
        portfolio_value: Decimal | None,
        total_cost_basis: Decimal,
        last_portfolio_value: Decimal | None,
        base_portfolio_value: Decimal | None,
        has_prices: bool,
        is_trading_day: bool,
    ) -> SnapshotBuildResult:
        next_base = base_portfolio_value
        next_last = last_portfolio_value
        returns = self._empty_returns()

        if has_prices and portfolio_value is not None:
            if next_base is None:
                next_base = portfolio_value

            returns = self._calculate_returns(
                portfolio_value=portfolio_value,
                total_cost_basis=total_cost_basis,
                last_portfolio_value=last_portfolio_value,
                base_portfolio_value=next_base,
            )
            next_last = portfolio_value
        return SnapshotBuildResult(
            snapshot=DailyPortfolioSnapshot(
                total_cost_basis=total_cost_basis,
                date=current_date,
                total_value=portfolio_value,
                daily_return_pct=returns["daily_return"],
                cumulative_return_pct=returns["cumulative_return"],
                daily_pnl=returns["daily_pnl"],
                cumulative_pnl=returns["cumulative_pnl"],
                status=self._status_for(current_date, has_prices, is_trading_day),
            ),
            base_portfolio_value=next_base,
            last_portfolio_value=next_last,
        )

    @staticmethod
    def _empty_returns() -> dict:
        return {
            "daily_pnl": None,
            "daily_return": None,
            "cumulative_pnl": None,
            "cumulative_return": None,
        }

    def _calculate_returns(
        self,
        portfolio_value: Decimal,
        total_cost_basis: Decimal,
        last_portfolio_value: Decimal | None,
        base_portfolio_value: Decimal | None,
    ) -> dict:
        returns = self._empty_returns()
        if last_portfolio_value is not None:
            returns["daily_pnl"] = portfolio_value - last_portfolio_value
            returns["daily_return"] = returns["daily_pnl"] / last_portfolio_value
        elif total_cost_basis > 0:
            returns["daily_pnl"] = portfolio_value - total_cost_basis
            returns["daily_return"] = returns["daily_pnl"] / total_cost_basis

        if base_portfolio_value is not None:
            returns["cumulative_pnl"], returns["cumulative_return"] = self._cumulative_return(
                portfolio_value,
                total_cost_basis,
                base_portfolio_value,
            )
        return returns

    @staticmethod
    def _cumulative_return(
        portfolio_value: Decimal,
        total_cost_basis: Decimal,
        base_portfolio_value: Decimal,
    ) -> tuple[Decimal, Decimal]:
        if total_cost_basis > 0:
            cumulative_pnl = portfolio_value - total_cost_basis
            return cumulative_pnl, cumulative_pnl / total_cost_basis
        cumulative_pnl = portfolio_value - base_portfolio_value
        return cumulative_pnl, cumulative_pnl / base_portfolio_value

    @staticmethod
    def _status_for(current_date: date, has_prices: bool, is_trading_day: bool) -> PortfolioStatus:
        if has_prices:
            return PortfolioStatus.OPEN
        if current_date.weekday() >= 5:
            return PortfolioStatus.WEEKEND
        if not is_trading_day:
            return PortfolioStatus.MARKET_CLOSED
        return PortfolioStatus.NO_DATA
