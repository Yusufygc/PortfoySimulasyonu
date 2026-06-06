from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Dict, Optional

from src.application.services.market.trade_session_guard import ensure_trade_session_open
from src.domain.models.model_portfolio import (
    ModelPortfolioCashMovement,
    ModelPortfolioCashMovementType,
    ModelPortfolioTrade,
    ModelTradeSide,
)
from src.domain.models.stock import Stock


@dataclass(frozen=True)
class ModelPortfolioSimulationResult:
    cash: Decimal
    invested_capital: Decimal
    positions: Dict[int, int]
    valid_trades: list[ModelPortfolioTrade]
    valid_movements: list[ModelPortfolioCashMovement]
    violations: list[tuple[object, str]]


class ModelPortfolioTradeSimulator:
    def simulate(
        self,
        portfolio,
        trades,
        movements=None,
        candidate_marker: tuple | None = None,
        candidate_object=None,
    ):
        cash = portfolio.initial_cash
        invested_capital = portfolio.initial_cash
        positions: Dict[int, int] = defaultdict(int)
        valid_trades = []
        valid_movements = []
        violations = []
        prepared = self._prepared_events(trades, movements or [], candidate_marker, candidate_object)

        for event, marker in sorted(prepared, key=lambda item: self._event_sort_key(item[0])):
            if isinstance(event, ModelPortfolioCashMovement):
                cash, invested_capital = self._apply_movement(
                    event,
                    marker,
                    cash,
                    invested_capital,
                    valid_movements,
                    violations,
                )
                continue

            if event.side == ModelTradeSide.BUY:
                self._apply_buy(event, marker, positions, valid_trades, violations, lambda: cash)
                if not violations or violations[-1][0] != marker:
                    cash -= event.total_amount
                continue

            self._apply_sell(event, marker, positions, valid_trades, violations)
            if not violations or violations[-1][0] != marker:
                cash += event.total_amount

        return ModelPortfolioSimulationResult(
            cash=cash,
            invested_capital=invested_capital,
            positions=positions,
            valid_trades=valid_trades,
            valid_movements=valid_movements,
            violations=violations,
        )

    def _prepared_events(self, trades, movements, candidate_marker: tuple | None, candidate_object):
        events = list(trades) + list(movements)
        if candidate_marker is None and candidate_object is None:
            return [(event, self._event_marker(event)) for event in events]
        marker_target = candidate_object if candidate_object is not None else events[-1] if events else None
        return [
            (event, candidate_marker if event is marker_target else self._event_marker(event))
            for event in events
        ]

    @staticmethod
    def _apply_movement(movement, marker, cash, invested_capital, valid_movements, violations):
        if movement.type == ModelPortfolioCashMovementType.DEPOSIT:
            valid_movements.append(movement)
            return cash + movement.amount, invested_capital + movement.amount

        if movement.amount > cash:
            violations.append(
                (
                    marker,
                    f"Yetersiz nakit. Cekilecek: {movement.amount:.2f} TL, Mevcut: {cash:.2f} TL",
                )
            )
            return cash, invested_capital

        valid_movements.append(movement)
        return cash - movement.amount, invested_capital - movement.amount

    @staticmethod
    def _apply_buy(trade, marker, positions, valid_trades, violations, cash_getter) -> None:
        cash = cash_getter()
        if trade.total_amount > cash:
            violations.append(
                (
                    marker,
                    f"Yetersiz nakit. Gerekli: {trade.total_amount:.2f} TL, Mevcut: {cash:.2f} TL",
                )
            )
            return
        positions[trade.stock_id] += trade.quantity
        valid_trades.append(trade)

    @staticmethod
    def _apply_sell(trade, marker, positions, valid_trades, violations) -> None:
        available = positions[trade.stock_id]
        if trade.quantity > available:
            violations.append(
                (
                    marker,
                    f"Yetersiz pozisyon. Satmak istediğiniz: {trade.quantity}, Mevcut: {available}",
                )
            )
            return
        positions[trade.stock_id] -= trade.quantity
        valid_trades.append(trade)

    @staticmethod
    def _trade_sort_key(trade: ModelPortfolioTrade) -> tuple:
        return (
            trade.trade_date,
            trade.trade_time if trade.trade_time is not None else time.min,
            trade.id or 0,
        )

    @staticmethod
    def _trade_marker(trade: ModelPortfolioTrade) -> object:
        return ("model_trade", int(trade.id)) if trade.id is not None else ("model_trade_object", id(trade))

    @staticmethod
    def _movement_marker(movement: ModelPortfolioCashMovement) -> object:
        if movement.id is not None:
            return ("model_cash_movement", int(movement.id))
        return ("model_cash_movement_object", id(movement))

    def _event_marker(self, event) -> object:
        if isinstance(event, ModelPortfolioCashMovement):
            return self._movement_marker(event)
        return self._trade_marker(event)

    @classmethod
    def _event_sort_key(cls, event) -> tuple:
        if isinstance(event, ModelPortfolioCashMovement):
            return (
                event.movement_date,
                event.movement_time if event.movement_time is not None else time.min,
                0,
                event.id or 0,
            )
        key = cls._trade_sort_key(event)
        return key[0], key[1], 1, key[2]


class ModelPortfolioTradeService:
    def __init__(self, portfolio_repo, stock_repo, market_session_service=None) -> None:
        self._portfolio_repo = portfolio_repo
        self._stock_repo = stock_repo
        self._market_session_service = market_session_service
        self._simulator = ModelPortfolioTradeSimulator()

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
        portfolio, trade_side, all_trades, all_movements = self._prepare_add_trade(
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            side=side,
            quantity=quantity,
            price=price,
        )
        ensure_trade_session_open(self._market_session_service, trade_date, trade_time)

        trades_at = self._filter_trades_until(all_trades, as_of=(trade_date, trade_time))
        movements_at = self._filter_movements_until(all_movements, as_of=(trade_date, trade_time))
        sim_at = self._simulator.simulate(portfolio, trades_at, movements_at)
        self._validate_trade_capacity(
            trade_side=trade_side,
            stock_id=stock_id,
            quantity=quantity,
            price=price,
            sim_at=sim_at,
        )

        trade = self._build_trade(
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            trade_side=trade_side,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            trade_time=trade_time,
        )

        # Timeline doğrulama — önceden çekilen verilerle çalışır, yeniden DB'ye gitme.
        all_trades_sorted = sorted(all_trades, key=self._trade_sort_key)
        all_movements_sorted = sorted(all_movements, key=self._movement_sort_key)
        existing_result = self._simulator.simulate(portfolio, all_trades_sorted, all_movements_sorted)
        self._validate_candidate_timeline(
            portfolio_id,
            trade,
            portfolio=portfolio,
            existing_trades=existing_result.valid_trades,
            existing_movements=existing_result.valid_movements,
        )
        return self._portfolio_repo.insert_trade(trade)

    def _prepare_add_trade(
        self,
        portfolio_id: int,
        stock_id: int,
        side: str,
        quantity: int,
        price: Decimal,
    ):
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

        all_trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        all_movements = self._get_cash_movements(portfolio_id)
        return portfolio, trade_side, all_trades, all_movements

    @staticmethod
    def _validate_trade_capacity(
        trade_side: ModelTradeSide,
        stock_id: int,
        quantity: int,
        price: Decimal,
        sim_at: ModelPortfolioSimulationResult,
    ) -> None:
        total_amount = Decimal(quantity) * price
        if trade_side == ModelTradeSide.BUY:
            if total_amount > sim_at.cash:
                raise ValueError(
                    f"Yetersiz nakit. Gerekli: {total_amount:.2f} TL, Mevcut: {sim_at.cash:.2f} TL"
                )
            return

        available = sim_at.positions.get(stock_id, 0)
        if quantity > available:
            raise ValueError(
                f"Yetersiz pozisyon. Satmak istediğiniz: {quantity}, Mevcut: {available}"
            )

    @staticmethod
    def _build_trade(
        portfolio_id: int,
        stock_id: int,
        trade_side: ModelTradeSide,
        quantity: int,
        price: Decimal,
        trade_date: date,
        trade_time: Optional[time],
    ) -> ModelPortfolioTrade:
        if trade_side == ModelTradeSide.BUY:
            return ModelPortfolioTrade.create_buy(
                portfolio_id=portfolio_id,
                stock_id=stock_id,
                trade_date=trade_date,
                quantity=quantity,
                price=price,
                trade_time=trade_time,
            )
        return ModelPortfolioTrade.create_sell(
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            trade_date=trade_date,
            quantity=quantity,
            price=price,
            trade_time=trade_time,
        )

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
        ensure_trade_session_open(self._market_session_service, trade_date, trade_time)
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
            for stock_id, qty in self._simulate(portfolio_id, self._trades_until(portfolio_id, as_of), as_of=as_of).positions.items()
            if qty > 0
        }

    def get_remaining_cash(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ) -> Decimal:
        return self._simulate(portfolio_id, self._trades_until(portfolio_id, as_of), as_of=as_of).cash

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
        return self._simulate(portfolio_id, self._trades_until(portfolio_id, as_of), as_of=as_of).valid_trades

    def get_capital_movements(self, portfolio_id: int):
        return self._get_cash_movements(portfolio_id)

    def get_invested_capital(self, portfolio_id: int) -> Decimal:
        return self._simulate(portfolio_id, self._trades_until(portfolio_id)).invested_capital

    def add_capital_movement(
        self,
        portfolio_id: int,
        movement_type: str,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> ModelPortfolioCashMovement:
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")
        movement_kind = ModelPortfolioCashMovementType(movement_type)
        if amount <= 0:
            raise ValueError("Tutar pozitif olmalidir.")

        movement = self._build_capital_movement(
            portfolio_id=portfolio_id,
            movement_type=movement_kind,
            amount=amount,
            movement_date=movement_date,
            movement_time=movement_time,
            notes=notes,
        )
        all_trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        all_movements = self._get_cash_movements(portfolio_id)

        trades_at = self._filter_trades_until(all_trades, as_of=(movement_date, movement_time))
        movements_at = self._filter_movements_until(all_movements, as_of=(movement_date, movement_time))
        sim_at = self._simulator.simulate(portfolio, trades_at, movements_at)
        if movement_kind == ModelPortfolioCashMovementType.WITHDRAW and amount > sim_at.cash:
            raise ValueError(f"Yetersiz nakit. Cekilecek: {amount:.2f} TL, Mevcut: {sim_at.cash:.2f} TL")

        existing_result = self._simulator.simulate(
            portfolio,
            sorted(all_trades, key=self._trade_sort_key),
            sorted(all_movements, key=self._movement_sort_key),
        )
        self._validate_candidate_timeline(
            portfolio_id,
            movement,
            portfolio=portfolio,
            existing_trades=existing_result.valid_trades,
            existing_movements=existing_result.valid_movements,
        )
        return self._portfolio_repo.insert_cash_movement(movement)

    @staticmethod
    def _build_capital_movement(
        portfolio_id: int,
        movement_type: ModelPortfolioCashMovementType,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time],
        notes: Optional[str],
    ) -> ModelPortfolioCashMovement:
        if movement_type == ModelPortfolioCashMovementType.DEPOSIT:
            return ModelPortfolioCashMovement.create_deposit(
                portfolio_id=portfolio_id,
                amount=amount,
                movement_date=movement_date,
                movement_time=movement_time,
                notes=notes,
            )
        return ModelPortfolioCashMovement.create_withdraw(
            portfolio_id=portfolio_id,
            amount=amount,
            movement_date=movement_date,
            movement_time=movement_time,
            notes=notes,
        )

    def _trades_until(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ):
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        return self._filter_trades_until(trades, as_of)

    def _validate_candidate_timeline(
        self,
        portfolio_id: int,
        candidate,
        portfolio=None,
        existing_trades=None,
        existing_movements=None,
    ) -> None:
        # existing_trades = zaten geçerli trade'ler (violations dışlanmış).
        # Dışarıdan verilirse DB'ye gidilmez.
        if portfolio is None:
            portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if existing_trades is None or existing_movements is None:
            all_trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
            all_movements = self._get_cash_movements(portfolio_id)
            existing_result = self._simulator.simulate(
                portfolio,
                sorted(all_trades, key=self._trade_sort_key),
                sorted(all_movements, key=self._movement_sort_key),
            )
            existing_trades = existing_result.valid_trades
            existing_movements = existing_result.valid_movements

        candidate_marker = ("candidate", id(candidate))
        candidate_trades = list(existing_trades)
        candidate_movements = list(existing_movements)
        if isinstance(candidate, ModelPortfolioCashMovement):
            candidate_movements.append(candidate)
        else:
            candidate_trades.append(candidate)
        result = self._simulator.simulate(
            portfolio,
            candidate_trades,
            candidate_movements,
            candidate_marker=candidate_marker,
            candidate_object=candidate,
        )
        for marker, reason in result.violations:
            if marker == candidate_marker:
                raise ValueError(reason)
            raise ValueError(
                "Bu tarih/saat ile işlem, sonraki model portföy nakit veya lot akışını geçersiz hale getiriyor."
            )

    def _filter_trades_until(self, trades, as_of: date | tuple[date, time | None] | None = None):
        """Pre-fetched trade listesini as_of noktasına göre filtreler (DB çağrısı yok)."""
        if as_of is None:
            return sorted(trades, key=self._trade_sort_key)
        as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
        max_key = (as_date, as_time if as_time is not None else time.max, float("inf"))
        return sorted(
            (t for t in trades if self._trade_sort_key(t) <= max_key),
            key=self._trade_sort_key,
        )

    def _filter_movements_until(self, movements, as_of: date | tuple[date, time | None] | None = None):
        if as_of is None:
            return sorted(movements, key=self._movement_sort_key)
        as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
        max_key = (as_date, as_time if as_time is not None else time.max, float("inf"))
        return sorted(
            (movement for movement in movements if self._movement_sort_key(movement) <= max_key),
            key=self._movement_sort_key,
        )

    def _simulate(
        self,
        portfolio_id: int,
        trades,
        candidate_marker: tuple | None = None,
        as_of: date | tuple[date, time | None] | None = None,
    ):
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {portfolio_id}")
        movements = self._filter_movements_until(
            self._get_cash_movements(portfolio_id),
            as_of=as_of,
        )
        return self._simulator.simulate(portfolio, trades, movements, candidate_marker)

    def _get_cash_movements(self, portfolio_id: int):
        get_movements = getattr(self._portfolio_repo, "get_cash_movements_by_portfolio_id", None)
        if get_movements is None:
            return []
        return get_movements(portfolio_id)

    @staticmethod
    def _trade_sort_key(trade: ModelPortfolioTrade) -> tuple:
        return (
            trade.trade_date,
            trade.trade_time if trade.trade_time is not None else time.min,
            trade.id or 0,
        )

    @staticmethod
    def _movement_sort_key(movement: ModelPortfolioCashMovement) -> tuple:
        return (
            movement.movement_date,
            movement.movement_time if movement.movement_time is not None else time.min,
            movement.id or 0,
        )

