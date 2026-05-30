from __future__ import annotations

from collections import defaultdict
from datetime import date, time as dt_time
from decimal import Decimal
from typing import Dict, List, Tuple

from src.application.services.portfolio.safe_portfolio_builder import (
    PortfolioBuildResult,
    build_portfolio_safely,
    trade_sort_key,
)
from src.domain.models.cash_movement import CashMovementType
from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade, TradeSide
from src.domain.ports.repositories.i_cash_movement_repo import ICashMovementRepository
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
        cash_movement_repo: ICashMovementRepository | None = None,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo
        self._cash_movement_repo = cash_movement_repo

    def get_current_portfolio(self) -> Portfolio:
        return self.get_portfolio_health().portfolio

    def get_portfolio_health(self, as_of: date | tuple[date, dt_time | None] | None = None) -> PortfolioBuildResult:
        return build_portfolio_safely(self._trades_until(as_of))

    def get_valid_trades(self, as_of: date | tuple[date, dt_time | None] | None = None) -> List[Trade]:
        return self.get_portfolio_health(as_of=as_of).valid_trades

    def get_portfolio_with_prices_for_date(
        self,
        value_date: date,
    ) -> Tuple[Portfolio, Dict[int, Decimal]]:
        portfolio = self.get_current_portfolio()
        price_map = self._price_repo.get_prices_for_date(value_date)
        return portfolio, price_map

    def add_trade(self, trade: Trade) -> Trade:
        return self._portfolio_repo.insert_trade(trade)

    def get_trades_for_stock(self, stock_id: int) -> List[Trade]:
        return self._portfolio_repo.get_trades_by_stock(stock_id)

    def calculate_capital(self) -> Decimal:
        return self.get_cash_balance()

    def get_cash_balance(self, as_of: date | tuple[date, dt_time | None] | None = None) -> Decimal:
        balance = Decimal("0")
        for _event_date, _event_time, _event_order, _event_id, event_type, amount in self._cash_events_until(as_of):
            if event_type in ("DEPOSIT", "SELL"):
                balance += amount
            else:
                balance -= amount
                if balance < 0:
                    balance = Decimal("0")
        return balance

    def validate_trade(self, trade: Trade) -> None:
        if trade.quantity <= 0:
            raise ValueError("Lot adedi pozitif olmalıdır.")
        if trade.price <= 0:
            raise ValueError("Fiyat pozitif olmalıdır.")

        as_of = (trade.trade_date, trade.trade_time)
        if trade.side == TradeSide.BUY:
            cash_balance = self.get_cash_balance(as_of=as_of)
            if trade.total_amount > cash_balance:
                raise ValueError(
                    f"Yetersiz nakit. Gerekli: {trade.total_amount:.2f} TL, Mevcut: {cash_balance:.2f} TL"
                )
            self._validate_candidate_timeline(trade)
            return

        available_quantity = self.get_position_quantity_as_of(
            stock_id=trade.stock_id,
            as_of=as_of,
        )
        if trade.quantity > available_quantity:
            raise ValueError(
                f"Yetersiz pozisyon. Satmak istediğiniz: {trade.quantity}, Mevcut: {available_quantity}"
            )
        self._validate_candidate_timeline(trade)

    def get_position_quantity_as_of(
        self,
        stock_id: int,
        as_of: date | tuple[date, dt_time | None] | None = None,
    ) -> int:
        portfolio = self.get_portfolio_health(as_of=as_of).portfolio
        position = portfolio.positions.get(stock_id)
        return position.total_quantity if position else 0

    def get_all_trades(self) -> List[Trade]:
        return self._portfolio_repo.get_all_trades()

    def get_first_trade_date(self):
        trades = self._portfolio_repo.get_all_trades()
        if not trades:
            return None
        return min(trade.trade_date for trade in trades)

    def _trades_until(self, as_of: date | tuple[date, dt_time | None] | None = None) -> List[Trade]:
        trades = self._portfolio_repo.get_all_trades()
        if as_of is None:
            return trades
        as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
        max_key = (as_date, as_time or dt_time.max, float("inf"))
        return [trade for trade in trades if trade_sort_key(trade) <= max_key]

    def _cash_movements_balance(self, as_of: date | tuple[date, dt_time | None] | None = None) -> Decimal:
        balance = Decimal("0")
        for _event_date, _event_time, _event_order, _event_id, event_type, amount in self._cash_movement_events_until(as_of):
            if event_type == "DEPOSIT":
                balance += amount
            else:
                balance -= amount
                if balance < 0:
                    balance = Decimal("0")
        return balance

    def _cash_events_until(
        self,
        as_of: date | tuple[date, dt_time | None] | None = None,
    ) -> list[tuple[date, dt_time, int, int, str, Decimal]]:
        events = self._cash_movement_events_until(as_of)
        for trade in self.get_valid_trades(as_of=as_of):
            event_type = "BUY" if trade.side == TradeSide.BUY else "SELL"
            events.append(
                (
                    trade.trade_date,
                    trade.trade_time or dt_time.min,
                    20,
                    int(trade.id or 0),
                    event_type,
                    trade.total_amount,
                )
            )
        return sorted(events, key=lambda event: (event[0], event[1], event[2], event[3]))

    def _cash_movement_events_until(
        self,
        as_of: date | tuple[date, dt_time | None] | None = None,
    ) -> list[tuple[date, dt_time, int, int, str, Decimal]]:
        if self._cash_movement_repo is None:
            return []

        if as_of is None:
            movements = self._cash_movement_repo.get_all_movements()
        elif isinstance(as_of, tuple):
            movements = self._cash_movement_repo.get_movements_until(as_of[0], as_of[1])
        else:
            movements = self._cash_movement_repo.get_movements_until(as_of)

        events: list[tuple[date, dt_time, int, int, str, Decimal]] = []
        for movement in movements:
            event_type = "DEPOSIT" if movement.type == CashMovementType.DEPOSIT else "WITHDRAW"
            event_order = 0 if movement.type == CashMovementType.DEPOSIT else 30
            events.append(
                (
                    movement.movement_date,
                    movement.movement_time or dt_time.min,
                    event_order,
                    int(movement.id or 0),
                    event_type,
                    movement.amount,
                )
            )
        return events

    def _validate_candidate_timeline(self, candidate: Trade) -> None:
        existing_trades = self.get_valid_trades()
        baseline_violations = {
            marker for marker, _reason in self._timeline_violations(existing_trades)
        }
        candidate_marker = ("candidate", id(candidate))
        candidate_violations = self._timeline_violations(
            list(existing_trades) + [candidate],
            candidate_marker=candidate_marker,
        )

        for marker, reason in candidate_violations:
            if marker == candidate_marker:
                raise ValueError(reason)
            if marker not in baseline_violations:
                raise ValueError(
                    "Bu tarih/saat ile işlem, sonraki nakit veya lot akışını geçersiz hale getiriyor."
                )

    def _timeline_violations(
        self,
        trades: list[Trade],
        candidate_marker: tuple | None = None,
    ) -> list[tuple[object, str]]:
        cash = Decimal("0")
        positions: dict[int, int] = defaultdict(int)
        violations: list[tuple[object, str]] = []

        events: list[tuple[date, dt_time, int, int, str, object, object]] = []
        for event_date, event_time, event_order, event_id, event_type, amount in self._cash_movement_events_until():
            events.append((event_date, event_time, event_order, event_id, event_type, amount, None))

        for index, trade in enumerate(trades):
            marker = candidate_marker if candidate_marker is not None and index == len(trades) - 1 else self._trade_marker(trade)
            events.append(
                (
                    trade.trade_date,
                    trade.trade_time or dt_time.min,
                    20,
                    int(trade.id or (10**12 if marker == candidate_marker else 0)),
                    "TRADE",
                    trade,
                    marker,
                )
            )

        events.sort(key=lambda event: (event[0], event[1], event[2], event[3]))
        for _event_date, _event_time, _event_order, event_id, event_type, payload, marker in events:
            if event_type == "DEPOSIT":
                cash += payload
                continue
            if event_type == "WITHDRAW":
                if payload > cash:
                    violations.append((marker or ("cash", event_id), "Yetersiz nakit. Nakit çekimi bakiyeyi aşıyor."))
                    cash = Decimal("0")
                else:
                    cash -= payload
                continue

            trade = payload
            if trade.side == TradeSide.BUY:
                if trade.total_amount > cash:
                    violations.append(
                        (
                            marker,
                            f"Yetersiz nakit. Gerekli: {trade.total_amount:.2f} TL, Mevcut: {cash:.2f} TL",
                        )
                    )
                    cash = Decimal("0")
                else:
                    cash -= trade.total_amount
                positions[trade.stock_id] += trade.quantity
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

        return violations

    @staticmethod
    def _trade_marker(trade: Trade) -> object:
        return ("trade", int(trade.id)) if trade.id is not None else ("trade_object", id(trade))
