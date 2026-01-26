# src/infrastructure/db/model_portfolio_repository.py

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import List, Optional

from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade, ModelTradeSide
from src.domain.services_interfaces.i_model_portfolio_repo import IModelPortfolioRepository
from .mysql_connection import MySQLConnectionProvider


class MySQLModelPortfolioRepository(IModelPortfolioRepository):
    """
    IModelPortfolioRepository'nin MySQL implementasyonu.
    'model_portfolios' ve 'model_portfolio_trades' tablolarına erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    # ---------- Row → Domain Mappers ---------- #

    def _row_to_model_portfolio(self, row: dict) -> ModelPortfolio:
        initial_cash = row.get("initial_cash")
        if initial_cash is not None and not isinstance(initial_cash, Decimal):
            initial_cash = Decimal(str(initial_cash))

        return ModelPortfolio(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            initial_cash=initial_cash or Decimal("100000.00"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_model_portfolio_trade(self, row: dict) -> ModelPortfolioTrade:
        price_val = row["price"]
        if not isinstance(price_val, Decimal):
            price_val = Decimal(str(price_val))

        trade_time: Optional[time] = row.get("trade_time")
        
        return ModelPortfolioTrade(
            id=row["id"],
            portfolio_id=row["portfolio_id"],
            stock_id=row["stock_id"],
            trade_date=row["trade_date"],
            trade_time=trade_time,
            side=ModelTradeSide(row["side"]),
            quantity=row["quantity"],
            price=price_val,
            created_at=row.get("created_at"),
        )

    # ---------- ModelPortfolio READ operasyonları ---------- #

    def get_all_model_portfolios(self) -> List[ModelPortfolio]:
        sql = """
            SELECT id, name, description, initial_cash, created_at, updated_at
            FROM model_portfolios
            ORDER BY name
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_model_portfolio(r) for r in rows]

    def get_model_portfolio_by_id(self, portfolio_id: int) -> Optional[ModelPortfolio]:
        sql = """
            SELECT id, name, description, initial_cash, created_at, updated_at
            FROM model_portfolios
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (portfolio_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_model_portfolio(row)

    # ---------- ModelPortfolio WRITE operasyonları ---------- #

    def create_model_portfolio(self, portfolio: ModelPortfolio) -> ModelPortfolio:
        sql = """
            INSERT INTO model_portfolios (name, description, initial_cash)
            VALUES (%s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                portfolio.name,
                portfolio.description,
                str(portfolio.initial_cash),
            ))
            portfolio_id = cursor.lastrowid

        return ModelPortfolio(
            id=portfolio_id,
            name=portfolio.name,
            description=portfolio.description,
            initial_cash=portfolio.initial_cash,
            created_at=None,
            updated_at=None,
        )

    def update_model_portfolio(self, portfolio: ModelPortfolio) -> None:
        if portfolio.id is None:
            raise ValueError("Portfolio id is required for update")

        sql = """
            UPDATE model_portfolios
            SET name = %s,
                description = %s,
                initial_cash = %s
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                portfolio.name,
                portfolio.description,
                str(portfolio.initial_cash),
                portfolio.id,
            ))

    def delete_model_portfolio(self, portfolio_id: int) -> None:
        sql = "DELETE FROM model_portfolios WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (portfolio_id,))

    # ---------- ModelPortfolioTrade READ operasyonları ---------- #

    def get_trades_by_portfolio_id(self, portfolio_id: int) -> List[ModelPortfolioTrade]:
        sql = """
            SELECT id, portfolio_id, stock_id, trade_date, trade_time, side, quantity, price, created_at
            FROM model_portfolio_trades
            WHERE portfolio_id = %s
            ORDER BY trade_date, trade_time, id
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (portfolio_id,))
            rows = cursor.fetchall()

        return [self._row_to_model_portfolio_trade(r) for r in rows]

    def get_trade_by_id(self, trade_id: int) -> Optional[ModelPortfolioTrade]:
        sql = """
            SELECT id, portfolio_id, stock_id, trade_date, trade_time, side, quantity, price, created_at
            FROM model_portfolio_trades
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (trade_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_model_portfolio_trade(row)

    # ---------- ModelPortfolioTrade WRITE operasyonları ---------- #

    def insert_trade(self, trade: ModelPortfolioTrade) -> ModelPortfolioTrade:
        sql = """
            INSERT INTO model_portfolio_trades (portfolio_id, stock_id, trade_date, trade_time, side, quantity, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                trade.portfolio_id,
                trade.stock_id,
                trade.trade_date,
                trade.trade_time,
                trade.side.value,
                trade.quantity,
                str(trade.price),
            ))
            trade_id = cursor.lastrowid

        return ModelPortfolioTrade(
            id=trade_id,
            portfolio_id=trade.portfolio_id,
            stock_id=trade.stock_id,
            trade_date=trade.trade_date,
            trade_time=trade.trade_time,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            created_at=None,
        )

    def delete_trade(self, trade_id: int) -> None:
        sql = "DELETE FROM model_portfolio_trades WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (trade_id,))

    def delete_all_trades_by_portfolio_id(self, portfolio_id: int) -> None:
        sql = "DELETE FROM model_portfolio_trades WHERE portfolio_id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (portfolio_id,))
