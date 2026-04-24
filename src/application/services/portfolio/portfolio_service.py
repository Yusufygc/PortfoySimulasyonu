from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Tuple

from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade, TradeSide
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository


class PortfolioService:
    """
    Portfoy ile ilgili temel islemleri yoneten application servisi.
    """

    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo

    def get_current_portfolio(self) -> Portfolio:
        trades: List[Trade] = self._portfolio_repo.get_all_trades()
        return Portfolio.from_trades(trades)

    def get_portfolio_with_prices_for_date(
        self,
        value_date: date,
    ) -> Tuple[Portfolio, Dict[int, Decimal]]:
        portfolio = self.get_current_portfolio()
        price_map = self._price_repo.get_prices_for_date(value_date)
        return portfolio, price_map

    def add_trade(self, trade: Trade) -> Trade:
        trades: List[Trade] = self._portfolio_repo.get_all_trades()
        portfolio = Portfolio.from_trades(trades)
        portfolio.apply_trade(trade)
        return self._portfolio_repo.insert_trade(trade)

    def get_trades_for_stock(self, stock_id: int) -> List[Trade]:
        all_trades = self._portfolio_repo.get_all_trades()
        return [trade for trade in all_trades if trade.stock_id == stock_id]

    def calculate_capital(self) -> Decimal:
        trades = self._portfolio_repo.get_all_trades()
        capital = Decimal("0")
        for trade in trades:
            trade_amount = trade.price * Decimal(trade.quantity)
            if trade.side == TradeSide.SELL:
                capital += trade_amount
            else:
                capital -= trade_amount
        return max(Decimal("0"), capital)

    def get_all_trades(self) -> List[Trade]:
        return self._portfolio_repo.get_all_trades()

    def get_first_trade_date(self):
        trades = self._portfolio_repo.get_all_trades()
        if not trades:
            return None
        return min(trade.trade_date for trade in trades)

