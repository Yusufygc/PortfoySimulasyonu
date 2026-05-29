from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Dict, Optional

from src.domain.models.model_portfolio import ModelPortfolioTrade, ModelTradeSide
from src.domain.models.stock import Stock


@dataclass(frozen=True)
class ModelPortfolioSimulationResult:
    cash: Decimal
    positions: Dict[int, int]
    valid_trades: list[ModelPortfolioTrade]
    violations: list[tuple[object, str]]


class ModelPortfolioTradeService:
    def __init__(self, portfolio_repo, stock_repo) -> None:
        self._portfolio_repo = portfolio_repo
        self._stock_repo = stock_repo

    def get_portfolio_trades(self, portfolio_id: int):
        return self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)

    def get_first_trade_date(self, portfolio_id: int) -> date | None:
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        if not trades:
            return None
        return min(trade.trade_date for trade in trades)

    def get_stock_trades(self, portfolio_id: int, stock_id: int):
        return [
            trade
            for trade in self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
            if trade.stock_id == stock_id
        ]

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
        if quantity <= 0:
            raise ValueError("Lot adedi pozitif olmalidir.")
        if price <= 0:
            raise ValueError("Fiyat pozitif olmalidir.")

        # Ön kontrol — add_trade_by_ticker ile tutarlı olsun (ana portföy validate_trade deseni).
        if trade_side == ModelTradeSide.BUY:
            total_amount = Decimal(quantity) * price
            remaining_cash = self.get_remaining_cash(portfolio_id, as_of=(trade_date, trade_time))
            if total_amount > remaining_cash:
                raise ValueError(
                    f"Yetersiz nakit. Gerekli: {total_amount:.2f} TL, Mevcut: {remaining_cash:.2f} TL"
                )
        else:
            available = self.get_position_quantity_as_of(portfolio_id, stock_id, as_of=(trade_date, trade_time))
            if quantity > available:
                raise ValueError(
                    f"Yetersiz pozisyon. Satmak istediğiniz: {quantity}, Mevcut: {available}"
                )

        if trade_side == ModelTradeSide.BUY:
            trade = ModelPortfolioTrade.create_buy(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )
        else:
            trade = ModelPortfolioTrade.create_sell(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )

        self._validate_candidate_timeline(portfolio_id, trade)
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

        trade_side = ModelTradeSide(side)
        if quantity <= 0:
            raise ValueError("Lot adedi pozitif olmalidir.")
        if price <= 0:
            raise ValueError("Fiyat pozitif olmalidir.")
        if trade_side == ModelTradeSide.BUY:
            total_amount = Decimal(quantity) * price
            remaining_cash = self.get_remaining_cash(portfolio_id, as_of=(trade_date, trade_time))
            if total_amount > remaining_cash:
                raise ValueError(
                    f"Yetersiz nakit. Gerekli: {total_amount:.2f} TL, Mevcut: {remaining_cash:.2f} TL"
                )
        stock = self._stock_repo.get_stock_by_ticker(normalized_ticker)
        if stock is None:
            if trade_side != ModelTradeSide.BUY:
                raise ValueError(f"Hisse bulunamadi: {normalized_ticker}")
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

    def get_positions(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ) -> Dict[int, int]:
        return {
            stock_id: qty
            for stock_id, qty in self._simulate(portfolio_id, self._trades_until(portfolio_id, as_of)).positions.items()
            if qty > 0
        }

    def get_remaining_cash(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ) -> Decimal:
        return self._simulate(portfolio_id, self._trades_until(portfolio_id, as_of)).cash

    def get_position_quantity_as_of(
        self,
        portfolio_id: int,
        stock_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ) -> int:
        return self.get_positions(portfolio_id, as_of=as_of).get(stock_id, 0)

    def get_valid_trades(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ):
        return self._simulate(portfolio_id, self._trades_until(portfolio_id, as_of)).valid_trades

    def _trades_until(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ):
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        if as_of is None:
            return sorted(trades, key=self._trade_sort_key)
        as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
        max_key = (as_date, as_time or time.max, float("inf"))
        return sorted((trade for trade in trades if self._trade_sort_key(trade) <= max_key), key=self._trade_sort_key)

    def _validate_candidate_timeline(self, portfolio_id: int, candidate: ModelPortfolioTrade) -> None:
        existing_trades = self.get_valid_trades(portfolio_id)
        baseline_violations = {
            marker for marker, _reason in self._simulate(portfolio_id, existing_trades).violations
        }
        candidate_marker = ("candidate", id(candidate))
        result = self._simulate(
            portfolio_id,
            list(existing_trades) + [candidate],
            candidate_marker=candidate_marker,
        )
        for marker, reason in result.violations:
            if marker == candidate_marker:
                raise ValueError(reason)
            if marker not in baseline_violations:
                raise ValueError(
                    "Bu tarih/saat ile işlem, sonraki model portföy nakit veya lot akışını geçersiz hale getiriyor."
                )

    def _simulate(self, portfolio_id: int, trades, candidate_marker: tuple | None = None):
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")

        cash = portfolio.initial_cash
        positions: Dict[int, int] = defaultdict(int)
        valid_trades = []
        violations = []

        candidate_trade = trades[-1] if candidate_marker is not None and trades else None
        prepared = [
            (trade, candidate_marker if trade is candidate_trade else self._trade_marker(trade))
            for trade in trades
        ]

        for trade, marker in sorted(prepared, key=lambda item: self._trade_sort_key(item[0])):
            if trade.side == ModelTradeSide.BUY:
                if trade.total_amount > cash:
                    # BUY ihlali SELL ile simetrik: lot ekleme, nakdi bozma, tamamen reddet.
                    violations.append(
                        (
                            marker,
                            f"Yetersiz nakit. Gerekli: {trade.total_amount:.2f} TL, Mevcut: {cash:.2f} TL",
                        )
                    )
                    continue
                cash -= trade.total_amount
                positions[trade.stock_id] += trade.quantity
                valid_trades.append(trade)
            else:
                available = positions[trade.stock_id]
                if trade.quantity > available:
                    violations.append(
                        (
                            marker,
                            f"Yetersiz pozisyon. Satmak istediğiniz: {trade.quantity}, Mevcut: {available}",
                        )
                    )
                    continue
                positions[trade.stock_id] -= trade.quantity
                cash += trade.total_amount
                valid_trades.append(trade)

        return ModelPortfolioSimulationResult(
            cash=cash,
            positions=positions,
            valid_trades=valid_trades,
            violations=violations,
        )

    @staticmethod
    def _trade_sort_key(trade: ModelPortfolioTrade) -> tuple:
        return (
            trade.trade_date,
            trade.trade_time or time.min,
            trade.id or 0,
        )

    @staticmethod
    def _trade_marker(trade: ModelPortfolioTrade) -> object:
        return ("model_trade", int(trade.id)) if trade.id is not None else ("model_trade_object", id(trade))
