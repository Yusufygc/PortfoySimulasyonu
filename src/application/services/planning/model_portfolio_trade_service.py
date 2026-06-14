from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Dict, NamedTuple, Optional

from src.application.services.market.trade_session_guard import ensure_trade_session_open
from src.domain.models.model_portfolio import (
    ModelPortfolioCashMovement,
    ModelPortfolioCashMovementType,
    ModelPortfolioTrade,
    ModelPortfolioTradeSpec,
    ModelTradeSide,
)
from src.domain.models.stock import Stock
from src.domain.constants.bist_tickers import is_valid_bist_ticker


class _SimAccumulators(NamedTuple):
    positions: "Dict[int, int]"
    valid_trades: list
    valid_movements: list
    violations: list


class CapitalMovementSpec(NamedTuple):
    portfolio_id: int
    movement_type: str
    amount: Decimal
    movement_date: date
    movement_time: "Optional[time]" = None
    notes: "Optional[str]" = None


class ModelTradeSpec(NamedTuple):
    portfolio_id: int
    stock_id: int
    side: str
    quantity: int
    price: Decimal
    trade_date: date
    trade_time: "Optional[time]" = None


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
        acc = _SimAccumulators(positions, valid_trades, valid_movements, violations)
        prepared = self._prepared_events(trades, movements or [], candidate_marker, candidate_object)

        for event, marker in sorted(prepared, key=lambda item: self._event_sort_key(item[0])):
            if isinstance(event, ModelPortfolioCashMovement):
                cash, invested_capital = self._apply_movement(event, marker, cash, invested_capital, acc)
                continue

            if event.side == ModelTradeSide.BUY:
                self._apply_buy(event, marker, acc, lambda: cash)
                if not violations or violations[-1][0] != marker:
                    cash -= event.total_amount
                continue

            self._apply_sell(event, marker, acc)
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
    def _apply_movement(movement, marker, cash, invested_capital, acc: "_SimAccumulators"):
        if movement.type == ModelPortfolioCashMovementType.DEPOSIT:
            acc.valid_movements.append(movement)
            return cash + movement.amount, invested_capital + movement.amount

        if movement.amount > cash:
            acc.violations.append(
                (
                    marker,
                    f"Yetersiz nakit. Cekilecek: {movement.amount:.2f} TL, Mevcut: {cash:.2f} TL",
                )
            )
            return cash, invested_capital

        acc.valid_movements.append(movement)
        return cash - movement.amount, invested_capital - movement.amount

    @staticmethod
    def _apply_buy(trade, marker, acc: "_SimAccumulators", cash_getter) -> None:
        cash = cash_getter()
        if trade.total_amount > cash:
            acc.violations.append(
                (
                    marker,
                    f"Yetersiz nakit. Gerekli: {trade.total_amount:.2f} TL, Mevcut: {cash:.2f} TL",
                )
            )
            return
        acc.positions[trade.stock_id] += trade.quantity
        acc.valid_trades.append(trade)

    @staticmethod
    def _apply_sell(trade, marker, acc: "_SimAccumulators") -> None:
        available = acc.positions[trade.stock_id]
        if trade.quantity > available:
            acc.violations.append(
                (
                    marker,
                    f"Yetersiz pozisyon. Satmak istediğiniz: {trade.quantity}, Mevcut: {available}",
                )
            )
            return
        acc.positions[trade.stock_id] -= trade.quantity
        acc.valid_trades.append(trade)

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


def _trade_sort_key(trade: ModelPortfolioTrade) -> tuple:
    return (
        trade.trade_date,
        trade.trade_time if trade.trade_time is not None else time.min,
        trade.id or 0,
    )


def _movement_sort_key(movement: ModelPortfolioCashMovement) -> tuple:
    return (
        movement.movement_date,
        movement.movement_time if movement.movement_time is not None else time.min,
        movement.id or 0,
    )


def _filter_trades_until(trades, as_of: date | tuple[date, time | None] | None = None):
    if as_of is None:
        return sorted(trades, key=_trade_sort_key)
    as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
    max_key = (as_date, as_time if as_time is not None else time.max, float("inf"))
    return sorted((trade for trade in trades if _trade_sort_key(trade) <= max_key), key=_trade_sort_key)


def _filter_movements_until(movements, as_of: date | tuple[date, time | None] | None = None):
    if as_of is None:
        return sorted(movements, key=_movement_sort_key)
    as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
    max_key = (as_date, as_time if as_time is not None else time.max, float("inf"))
    return sorted(
        (movement for movement in movements if _movement_sort_key(movement) <= max_key),
        key=_movement_sort_key,
    )


class _ModelTradeTarget(NamedTuple):
    portfolio_id: int
    stock_id: int
    trade_side: ModelTradeSide


def _build_trade(
    target: _ModelTradeTarget,
    quantity: int,
    price: Decimal,
    trade_date: date,
    trade_time: Optional[time],
) -> ModelPortfolioTrade:
    spec = ModelPortfolioTradeSpec(
        portfolio_id=target.portfolio_id,
        stock_id=target.stock_id,
        trade_date=trade_date,
        quantity=quantity,
        price=price,
        trade_time=trade_time,
    )
    factory = (
        ModelPortfolioTrade.create_buy
        if target.trade_side == ModelTradeSide.BUY
        else ModelPortfolioTrade.create_sell
    )
    return factory(spec)


def _build_capital_movement(spec: "CapitalMovementSpec") -> ModelPortfolioCashMovement:
    movement_kind = ModelPortfolioCashMovementType(spec.movement_type)
    factory = (
        ModelPortfolioCashMovement.create_deposit
        if movement_kind == ModelPortfolioCashMovementType.DEPOSIT
        else ModelPortfolioCashMovement.create_withdraw
    )
    return factory(
        portfolio_id=spec.portfolio_id,
        amount=spec.amount,
        movement_date=spec.movement_date,
        movement_time=spec.movement_time,
        notes=spec.notes,
    )


class ModelTradeInput(NamedTuple):
    side: str
    quantity: int
    price: Decimal
    trade_date: date
    trade_time: Optional[time] = None
    name: Optional[str] = None


def _normalize_ticker(ticker: str) -> str:
    if not ticker or not ticker.strip():
        raise ValueError("Ticker bos olamaz")
    normalized = ticker.strip().upper()
    if "." not in normalized:
        normalized += ".IS"
    return normalized


def _validate_quantity_price(quantity: int, price: Decimal) -> None:
    if quantity <= 0:
        raise ValueError("Lot adedi pozitif olmalidir.")
    if price <= 0:
        raise ValueError("Fiyat pozitif olmalidir.")


def _resolve_or_create_stock(stock_repo, ticker: str, trade_side, name: Optional[str]):
    stock = stock_repo.get_stock_by_ticker(ticker)
    if stock is None:
        if trade_side != ModelTradeSide.BUY:
            raise ValueError(f"Hisse bulunamadi: {ticker}")
        if not is_valid_bist_ticker(ticker, name):
            raise ValueError(f"Geçersiz hisse kodu: {ticker}")
        stock = stock_repo.insert_stock(
            Stock(
                id=None,
                ticker=ticker,
                name=(name or ticker).strip() or ticker,
                currency_code="TRY",
            )
        )
    return stock


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

    def add_trade(self, spec: "ModelTradeSpec") -> ModelPortfolioTrade:
        portfolio, trade_side, all_trades, all_movements = self._prepare_add_trade(
            portfolio_id=spec.portfolio_id,
            stock_id=spec.stock_id,
            side=spec.side,
            quantity=spec.quantity,
            price=spec.price,
        )
        ensure_trade_session_open(self._market_session_service, spec.trade_date, spec.trade_time)

        trades_at = _filter_trades_until(all_trades, as_of=(spec.trade_date, spec.trade_time))
        movements_at = _filter_movements_until(all_movements, as_of=(spec.trade_date, spec.trade_time))
        sim_at = self._simulator.simulate(portfolio, trades_at, movements_at)
        self._validate_trade_capacity(
            trade_side=trade_side,
            stock_id=spec.stock_id,
            quantity=spec.quantity,
            price=spec.price,
            sim_at=sim_at,
        )

        trade = _build_trade(
            _ModelTradeTarget(spec.portfolio_id, spec.stock_id, trade_side),
            quantity=spec.quantity,
            price=spec.price,
            trade_date=spec.trade_date,
            trade_time=spec.trade_time,
        )

        all_trades_sorted = sorted(all_trades, key=_trade_sort_key)
        all_movements_sorted = sorted(all_movements, key=_movement_sort_key)
        existing_result = self._simulator.simulate(portfolio, all_trades_sorted, all_movements_sorted)
        self._validate_candidate_timeline(
            spec.portfolio_id,
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

    def add_trade_by_ticker(
        self,
        portfolio_id: int,
        ticker: str,
        trade_input: ModelTradeInput,
    ) -> ModelPortfolioTrade:
        normalized_ticker = _normalize_ticker(ticker)
        trade_side = ModelTradeSide(trade_input.side)
        _validate_quantity_price(trade_input.quantity, trade_input.price)
        ensure_trade_session_open(self._market_session_service, trade_input.trade_date, trade_input.trade_time)
        stock = _resolve_or_create_stock(self._stock_repo, normalized_ticker, trade_side, trade_input.name)
        return self.add_trade(
            ModelTradeSpec(
                portfolio_id=portfolio_id,
                stock_id=stock.id,
                side=trade_input.side,
                quantity=trade_input.quantity,
                price=trade_input.price,
                trade_date=trade_input.trade_date,
                trade_time=trade_input.trade_time,
            )
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

    def add_capital_movement(self, spec: "CapitalMovementSpec") -> ModelPortfolioCashMovement:
        portfolio = self._portfolio_repo.get_model_portfolio_by_id(spec.portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfoy bulunamadi: {spec.portfolio_id}")
        movement_kind = ModelPortfolioCashMovementType(spec.movement_type)
        if spec.amount <= 0:
            raise ValueError("Tutar pozitif olmalidir.")

        movement = _build_capital_movement(spec)
        all_trades = self._portfolio_repo.get_trades_by_portfolio_id(spec.portfolio_id)
        all_movements = self._get_cash_movements(spec.portfolio_id)

        trades_at = _filter_trades_until(all_trades, as_of=(spec.movement_date, spec.movement_time))
        movements_at = _filter_movements_until(all_movements, as_of=(spec.movement_date, spec.movement_time))
        sim_at = self._simulator.simulate(portfolio, trades_at, movements_at)
        if movement_kind == ModelPortfolioCashMovementType.WITHDRAW and spec.amount > sim_at.cash:
            raise ValueError(f"Yetersiz nakit. Cekilecek: {spec.amount:.2f} TL, Mevcut: {sim_at.cash:.2f} TL")

        existing_result = self._simulator.simulate(
            portfolio,
            sorted(all_trades, key=_trade_sort_key),
            sorted(all_movements, key=_movement_sort_key),
        )
        self._validate_candidate_timeline(
            spec.portfolio_id,
            movement,
            portfolio=portfolio,
            existing_trades=existing_result.valid_trades,
            existing_movements=existing_result.valid_movements,
        )
        return self._portfolio_repo.insert_cash_movement(movement)

    def _trades_until(
        self,
        portfolio_id: int,
        as_of: date | tuple[date, time | None] | None = None,
    ):
        trades = self._portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
        return _filter_trades_until(trades, as_of)

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
                sorted(all_trades, key=_trade_sort_key),
                sorted(all_movements, key=_movement_sort_key),
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
        movements = _filter_movements_until(
            self._get_cash_movements(portfolio_id),
            as_of=as_of,
        )
        return self._simulator.simulate(portfolio, trades, movements, candidate_marker)

    def _get_cash_movements(self, portfolio_id: int):
        get_movements = getattr(self._portfolio_repo, "get_cash_movements_by_portfolio_id", None)
        if get_movements is None:
            return []
        return get_movements(portfolio_id)


