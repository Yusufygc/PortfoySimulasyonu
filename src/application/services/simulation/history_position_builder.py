from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from typing import NamedTuple

from src.application.services.reporting.daily_history_models import DailyPosition
from src.domain.models.portfolio import Portfolio


class _DayCtx(NamedTuple):
    prices_for_day: "dict[int, Decimal]"
    ticker_map: "dict[int, str]"
    last_close_by_stock: "dict[int, Decimal]"
    total_value: Decimal


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

        day_ctx = _DayCtx(prices_for_day, ticker_map, last_close_by_stock, total_value)
        for stock_id, position in portfolio.positions.items():
            daily_position = self._build_position(current_date, stock_id, position, day_ctx)
            if daily_position is None:
                continue
            positions.append(daily_position)

        portfolio_value = total_value if total_value > 0 else None
        return DailyPositionBuildResult(
            positions=positions,
            total_cost_basis=total_cost_basis,
            portfolio_value=portfolio_value,
            last_close_by_stock=prices_for_day.copy() if portfolio_value is not None else last_close_by_stock,
        )

    def _build_position(
        self,
        current_date: date,
        stock_id: int,
        position,
        ctx: _DayCtx,
    ) -> DailyPosition | None:
        qty = position.total_quantity
        if qty <= 0:
            return None
        metrics = self._position_metrics(stock_id, position, qty, ctx)
        return DailyPosition(
            date=current_date,
            ticker=ctx.ticker_map.get(stock_id, f"ID_{stock_id}"),
            quantity=qty,
            avg_cost=position.average_cost or Decimal("0"),
            cost_basis=position.total_cost,
            close_price=metrics["close_price"],
            position_value=metrics["position_value"],
            daily_price_change_pct=metrics["daily_change"],
            daily_pnl_tl=metrics["daily_pnl"],
            unrealized_pnl_tl=metrics["unrealized_tl"],
            unrealized_pnl_pct=metrics["unrealized_pct"],
            weight_pct=metrics["weight_pct"],
        )

    @staticmethod
    def _position_metrics(
        stock_id: int,
        position,
        quantity: int,
        ctx: _DayCtx,
    ) -> dict:
        close_price = ctx.prices_for_day.get(stock_id)
        if close_price is None:
            return {
                "close_price": None,
                "position_value": None,
                "daily_change": None,
                "daily_pnl": None,
                "unrealized_tl": None,
                "unrealized_pct": None,
                "weight_pct": None,
            }

        cost_basis = position.total_cost
        position_value = position.market_value(close_price)
        last_close = ctx.last_close_by_stock.get(stock_id)
        daily_change = (close_price / last_close) - 1 if last_close is not None and last_close != 0 else None
        unrealized_tl = position.unrealized_pl(close_price)
        daily_pnl = (close_price - last_close) * Decimal(quantity) if last_close is not None and last_close != 0 else unrealized_tl
        return {
            "close_price": close_price,
            "position_value": position_value,
            "daily_change": daily_change,
            "daily_pnl": daily_pnl,
            "unrealized_tl": unrealized_tl,
            "unrealized_pct": (unrealized_tl / cost_basis) if cost_basis != 0 else None,
            "weight_pct": (position_value / ctx.total_value) if ctx.total_value else None,
        }
