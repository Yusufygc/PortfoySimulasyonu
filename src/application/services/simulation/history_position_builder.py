from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.application.services.reporting.daily_history_models import DailyPosition
from src.domain.models.portfolio import Portfolio


@dataclass
class DailyPositionBuildResult:
    positions: list[DailyPosition]
    total_cost_basis: Decimal
    portfolio_value: Decimal | None
    last_close_by_stock: dict[int, Decimal]


class HistoryPositionBuilder:
    def build(
        self,
        current_date: date,
        portfolio: Portfolio,
        prices_for_day: dict[int, Decimal],
        ticker_map: dict[int, str],
        last_close_by_stock: dict[int, Decimal],
    ) -> DailyPositionBuildResult:
        total_value = portfolio.total_market_value(prices_for_day)
        total_cost_basis = portfolio.total_cost()
        positions: list[DailyPosition] = []

        for stock_id, position in portfolio.positions.items():
            qty = position.total_quantity
            if qty <= 0:
                continue

            avg_cost = position.average_cost or Decimal("0")
            cost_basis = position.total_cost
            close_price = prices_for_day.get(stock_id)

            if close_price is not None:
                pos_val = position.market_value(close_price)
                last_close = last_close_by_stock.get(stock_id)
                daily_chg = (
                    (close_price / last_close) - 1
                    if last_close is not None and last_close != 0
                    else None
                )
                unrealized_tl = position.unrealized_pl(close_price)
                unrealized_pct = (unrealized_tl / cost_basis) if cost_basis != 0 else None
                daily_pnl_stock = (
                    (close_price - last_close) * Decimal(qty)
                    if last_close is not None and last_close != 0
                    else unrealized_tl
                )
            else:
                pos_val = None
                daily_chg = None
                daily_pnl_stock = None
                unrealized_tl = None
                unrealized_pct = None

            weight_pct = (pos_val / total_value) if pos_val is not None and total_value else None
            positions.append(
                DailyPosition(
                    date=current_date,
                    ticker=ticker_map.get(stock_id, f"ID_{stock_id}"),
                    quantity=qty,
                    avg_cost=avg_cost,
                    cost_basis=cost_basis,
                    close_price=close_price,
                    position_value=pos_val,
                    daily_price_change_pct=daily_chg,
                    daily_pnl_tl=daily_pnl_stock,
                    unrealized_pnl_tl=unrealized_tl,
                    unrealized_pnl_pct=unrealized_pct,
                    weight_pct=weight_pct,
                )
            )

        portfolio_value = total_value if total_value > 0 else None
        return DailyPositionBuildResult(
            positions=positions,
            total_cost_basis=total_cost_basis,
            portfolio_value=portfolio_value,
            last_close_by_stock=prices_for_day.copy() if portfolio_value is not None else last_close_by_stock,
        )
