from __future__ import annotations

from dataclasses import dataclass
from datetime import time as dt_time
from typing import Iterable

from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade, TradeSide


@dataclass(frozen=True)
class InvalidTrade:
    trade: Trade
    reason: str
    available_quantity: int


@dataclass(frozen=True)
class PortfolioBuildResult:
    portfolio: Portfolio
    valid_trades: list[Trade]
    invalid_trades: list[InvalidTrade]


def trade_sort_key(trade: Trade) -> tuple:
    return (
        trade.trade_date,
        trade.trade_time or dt_time.min,
        trade.id or 0,
    )


def build_portfolio_safely(trades: Iterable[Trade], is_sorted: bool = False) -> PortfolioBuildResult:
    portfolio = Portfolio()
    valid_trades: list[Trade] = []
    invalid_trades: list[InvalidTrade] = []

    ordered_trades = trades if is_sorted else sorted(trades, key=trade_sort_key)
    for trade in ordered_trades:
        position = portfolio.positions.get(trade.stock_id)
        available_quantity = position.total_quantity if position else 0
        if trade.side == TradeSide.SELL and trade.quantity > available_quantity:
            invalid_trades.append(
                InvalidTrade(
                    trade=trade,
                    reason="Eldeki lottan fazla satış",
                    available_quantity=available_quantity,
                )
            )
            continue

        portfolio.apply_trade(trade)
        valid_trades.append(trade)

    return PortfolioBuildResult(
        portfolio=portfolio,
        valid_trades=valid_trades,
        invalid_trades=invalid_trades,
    )
