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
        daily_pnl = None
        daily_ret = None
        cumulative_pnl = None
        cumulative_ret = None
        next_base = base_portfolio_value
        next_last = last_portfolio_value

        if has_prices and portfolio_value is not None:
            if next_base is None:
                next_base = portfolio_value

            if last_portfolio_value is not None:
                daily_pnl = portfolio_value - last_portfolio_value
                daily_ret = daily_pnl / last_portfolio_value
            elif total_cost_basis > 0:
                daily_pnl = portfolio_value - total_cost_basis
                daily_ret = daily_pnl / total_cost_basis

            if next_base is not None:
                if portfolio_value == next_base and total_cost_basis > 0:
                    cumulative_pnl = portfolio_value - total_cost_basis
                    cumulative_ret = cumulative_pnl / total_cost_basis
                elif total_cost_basis > 0:
                    cumulative_pnl = portfolio_value - total_cost_basis
                    cumulative_ret = cumulative_pnl / total_cost_basis
                else:
                    cumulative_pnl = portfolio_value - next_base
                    cumulative_ret = cumulative_pnl / next_base

            next_last = portfolio_value

        if has_prices:
            status = PortfolioStatus.OPEN
        elif current_date.weekday() >= 5:
            status = PortfolioStatus.WEEKEND
        elif not is_trading_day:
            status = PortfolioStatus.MARKET_CLOSED
        else:
            status = PortfolioStatus.NO_DATA
        return SnapshotBuildResult(
            snapshot=DailyPortfolioSnapshot(
                total_cost_basis=total_cost_basis,
                date=current_date,
                total_value=portfolio_value,
                daily_return_pct=daily_ret,
                cumulative_return_pct=cumulative_ret,
                daily_pnl=daily_pnl,
                cumulative_pnl=cumulative_pnl,
                status=status,
            ),
            base_portfolio_value=next_base,
            last_portfolio_value=next_last,
        )
