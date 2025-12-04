# src/application/services/portfolio_service.py (sadece fikir)
from decimal import Decimal
from typing import Dict
from datetime import date

from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade
from src.domain.models.position import Position


class PortfolioService:
    def __init__(self, portfolio_repo, price_repo):
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo

    def get_current_portfolio(self) -> Portfolio:
        trades = self._portfolio_repo.get_all_trades()  # DB → Trade list
        return Portfolio.from_trades(trades)

    def add_trade(self, trade: Trade) -> None:
        # İş kuralı kontrolleri (örneğin satarken yeterli lot var mı vs.)
        # Gerekirse burada Position oluşturup önce simulate edersin.
        self._portfolio_repo.insert_trade(trade)

    def get_portfolio_with_prices_for_date(
        self, price_date: date ) -> (Portfolio, Dict[int, Decimal]):
        portfolio = self.get_current_portfolio()
        price_map = self._price_repo.get_prices_for_date(price_date)
        return portfolio, price_map
