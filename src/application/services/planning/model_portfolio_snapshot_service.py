from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.domain.models.model_portfolio import ModelTradeSide


class ModelPortfolioSnapshotService:
    def __init__(self, portfolio_repo, stock_repo, trade_service) -> None:
        self._portfolio_repo = portfolio_repo
        self._stock_repo = stock_repo
        self._trade_service = trade_service

    def get_portfolio_summary(
        self,
        portfolio_id: int,
        price_map: Optional[Dict[int, Decimal]] = None,
    ) -> Dict[str, Any]:
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")

        remaining_cash = self._trade_service.get_remaining_cash(portfolio_id)
        positions = self._trade_service.get_positions(portfolio_id)

        positions_value = Decimal("0")
        if price_map:
            for stock_id, quantity in positions.items():
                if stock_id in price_map:
                    positions_value += price_map[stock_id] * Decimal(quantity)

        total_value = remaining_cash + positions_value
        profit_loss = total_value - portfolio.initial_cash
        profit_loss_pct = (profit_loss / portfolio.initial_cash * 100) if portfolio.initial_cash > 0 else Decimal("0")
        return {
            "initial_cash": portfolio.initial_cash,
            "remaining_cash": remaining_cash,
            "positions_value": positions_value,
            "total_value": total_value,
            "profit_loss": profit_loss,
            "profit_loss_pct": profit_loss_pct,
        }

    def get_positions_with_details(
        self,
        portfolio_id: int,
        price_map: Optional[Dict[int, Decimal]] = None,
    ) -> List[Dict[str, Any]]:
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        positions = self._trade_service.get_positions(portfolio_id)
        if not positions:
            return []

        stock_ids = list(positions.keys())
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {stock.id: stock for stock in stocks}

        cost_data: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"qty": 0, "cost": Decimal("0")})
        for trade in trades:
            if trade.side == ModelTradeSide.BUY:
                cost_data[trade.stock_id]["qty"] += trade.quantity
                cost_data[trade.stock_id]["cost"] += trade.total_amount
            else:
                if cost_data[trade.stock_id]["qty"] > 0:
                    avg = cost_data[trade.stock_id]["cost"] / Decimal(cost_data[trade.stock_id]["qty"])
                    cost_data[trade.stock_id]["qty"] -= trade.quantity
                    cost_data[trade.stock_id]["cost"] -= avg * Decimal(trade.quantity)

        result = []
        for stock_id, quantity in positions.items():
            stock = stock_map.get(stock_id)
            total_cost = cost_data[stock_id]["cost"]
            avg_cost = total_cost / Decimal(quantity) if quantity > 0 else Decimal("0")
            current_price = price_map.get(stock_id) if price_map else None
            current_value = current_price * Decimal(quantity) if current_price else None
            profit_loss = current_value - total_cost if current_value else None
            result.append(
                {
                    "stock_id": stock_id,
                    "ticker": stock.ticker if stock else "?",
                    "name": stock.name if stock else "Bilinmeyen",
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                    "total_cost": total_cost,
                    "current_price": current_price,
                    "current_value": current_value,
                    "profit_loss": profit_loss,
                }
            )
        return result

    def get_trade_count(self, portfolio_id: int) -> int:
        return self._portfolio_repo.count_trades_by_portfolio_id(portfolio_id)

