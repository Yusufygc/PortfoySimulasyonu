from __future__ import annotations

from collections import defaultdict
from datetime import date, time
from decimal import Decimal
from typing import Dict, Optional

from src.domain.models.model_portfolio import ModelPortfolioTrade, ModelTradeSide
from src.domain.models.stock import Stock


class ModelPortfolioTradeService:
    def __init__(self, portfolio_repo, stock_repo) -> None:
        self._portfolio_repo = portfolio_repo
        self._stock_repo = stock_repo

    def get_portfolio_trades(self, portfolio_id: int):
        return self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)

    def add_trade(
        self,
        portfolio_id: int,
        stock_id: int,
        side: str,
        quantity: int,
        price: Decimal,
        trade_date: date,
        trade_time: Optional[time] = None,
    ) -> ModelPortfolioTrade:
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")

        stock = self._stock_repo.get_stock_by_id(stock_id)
        if stock is None:
            raise ValueError(f"Hisse bulunamadi: {stock_id}")

        trade_side = ModelTradeSide(side)
        total_cost = price * Decimal(quantity)

        if trade_side == ModelTradeSide.BUY:
            remaining_cash = self.get_remaining_cash(portfolio_id)
            if total_cost > remaining_cash:
                raise ValueError(
                    f"Yetersiz bakiye. Gerekli: {total_cost:.2f} TL, Mevcut: {remaining_cash:.2f} TL"
                )
            trade = ModelPortfolioTrade.create_buy(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )
        else:
            positions = self.get_positions(portfolio_id)
            current_qty = positions.get(stock_id, 0)
            if quantity > current_qty:
                raise ValueError(
                    f"Yetersiz pozisyon. Satmak istediginiz: {quantity}, Mevcut: {current_qty}"
                )
            trade = ModelPortfolioTrade.create_sell(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )

        return self._portfolio_repo.insert_trade(trade)

    def add_trade_by_ticker(
        self,
        portfolio_id: int,
        ticker: str,
        side: str,
        quantity: int,
        price: Decimal,
        trade_date: date,
        trade_time: Optional[time] = None,
    ) -> ModelPortfolioTrade:
        if not ticker or not ticker.strip():
            raise ValueError("Ticker bos olamaz")

        normalized_ticker = ticker.strip().upper()
        if "." not in normalized_ticker:
            normalized_ticker += ".IS"

        stock = self._stock_repo.get_stock_by_ticker(normalized_ticker)
        if stock is None:
            stock = self._stock_repo.insert_stock(
                Stock(id=None, ticker=normalized_ticker, name=normalized_ticker, currency_code="TRY")
            )

        return self.add_trade(
            portfolio_id=portfolio_id,
            stock_id=stock.id,
            side=side,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            trade_time=trade_time,
        )

    def delete_trade(self, trade_id: int) -> None:
        self._portfolio_repo.delete_trade(trade_id)

    def get_positions(self, portfolio_id: int) -> Dict[int, int]:
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        positions: Dict[int, int] = defaultdict(int)
        for trade in trades:
            if trade.side == ModelTradeSide.BUY:
                positions[trade.stock_id] += trade.quantity
            else:
                positions[trade.stock_id] -= trade.quantity
        return {stock_id: qty for stock_id, qty in positions.items() if qty > 0}

    def get_remaining_cash(self, portfolio_id: int) -> Decimal:
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")

        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        cash = portfolio.initial_cash
        for trade in trades:
            if trade.side == ModelTradeSide.BUY:
                cash -= trade.total_amount
            else:
                cash += trade.total_amount
        return cash

