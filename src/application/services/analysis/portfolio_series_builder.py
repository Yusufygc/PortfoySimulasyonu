from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence

from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely
from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.models.trade import Trade
from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository


def _movement_time_key(item):
    return item.movement_time or time.min


def _trade_time_key(item):
    return item.trade_time or time.min


def _apply_cash_movements(cash_movements, current_cash: Decimal) -> tuple:
    net_flow = Decimal("0")
    for cm in sorted(cash_movements, key=_movement_time_key):
        if cm.type == CashMovementType.DEPOSIT:
            current_cash += cm.amount
            net_flow += cm.amount
        elif cm.type == CashMovementType.WITHDRAW:
            current_cash -= cm.amount
            net_flow -= cm.amount
            if current_cash < 0:
                current_cash = Decimal("0")
    return current_cash, net_flow


class PortfolioSeriesRequest(NamedTuple):
    trades: "List[Trade]"
    cash_movements: "List[CashMovement]"
    stock_ids: "Sequence[int]"
    ticker_map: "Dict[int, str]"
    start_date: date
    end_date: date
    portfolio: "Portfolio"
    trade_stock_ids: "Sequence[int] | None" = None


class _SimLoopInput(NamedTuple):
    start_date: date
    end_date: date
    has_cash_tracking: bool
    current_cash: Decimal
    current_positions: dict
    trades_by_date: dict
    cash_by_date: dict
    prices_by_stock: dict
    last_prices: dict
    stock_ids: Sequence
    warnings: Optional[list] = None
    ticker_map: Optional[dict] = None


def _should_warn_missing_price(position, stock_id: int, warned_stocks: set) -> bool:
    return position.total_quantity > 0 and stock_id not in warned_stocks


def _emit_price_warning(warnings, ticker_map, stock_id: int, warned_stocks: set) -> None:
    if warnings is not None and ticker_map is not None:
        warnings.append(f"{ticker_map.get(stock_id, str(stock_id))} icin tarih araliginda fiyat verisi bulunamadi.")
        warned_stocks.add(stock_id)


def _sorted_trades_up_to_date(trades, end_date) -> list:
    return sorted(
        (trade for trade in trades if trade.trade_date <= end_date),
        key=lambda trade: (trade.trade_date, trade.trade_time or time.min, trade.id or 0),
    )


def _accumulate_active_stock_ids(portfolio, valid_trades, start_date) -> set:
    stock_ids = set(portfolio.active_positions)
    for trade in valid_trades:
        if trade.trade_date < start_date:
            continue
        portfolio.apply_trade(trade)
        if portfolio.positions[trade.stock_id].total_quantity > 0:
            stock_ids.add(trade.stock_id)
    return stock_ids


def _build_initial_positions(trades_before: list, stock_ids) -> dict:
    return {
        stock_id: Position.from_trades(stock_id, [t for t in trades_before if t.stock_id == stock_id])
        for stock_id in stock_ids
    }


class PortfolioSeriesBuilder:
    def __init__(
        self,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
    ) -> None:
        self._price_repo = price_repo
        self._stock_repo = stock_repo

    def resolve_stock_scope(
        self,
        trades: Iterable[Trade],
        selected_stock_ids: Sequence[int],
        as_of: date | None = None,
    ) -> List[int]:
        selected = [stock_id for stock_id in selected_stock_ids if stock_id]
        if selected:
            return sorted(set(selected))
        scoped_trades = [trade for trade in trades if as_of is None or trade.trade_date <= as_of]
        return sorted(build_portfolio_safely(scoped_trades).portfolio.active_positions)

    def resolve_valuation_stock_scope(
        self,
        trades: Iterable[Trade],
        selected_stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> List[int]:
        selected = [stock_id for stock_id in selected_stock_ids if stock_id]
        if selected:
            return sorted(set(selected))
        ordered_trades = _sorted_trades_up_to_date(trades, end_date)
        valid_trades = build_portfolio_safely(ordered_trades, is_sorted=True).valid_trades
        portfolio = build_portfolio_safely(
            (trade for trade in valid_trades if trade.trade_date < start_date),
            is_sorted=True,
        ).portfolio
        return sorted(_accumulate_active_stock_ids(portfolio, valid_trades, start_date))

    def compute_portfolio_series(
        self,
        req: PortfolioSeriesRequest,
    ) -> tuple[Dict[date, Decimal], Dict[date, Decimal], Dict[int, Decimal], List[str]]:
        trade_scope = sorted(set(req.trade_stock_ids if req.trade_stock_ids is not None else {t.stock_id for t in req.trades}))
        if not req.stock_ids and not trade_scope:
            return {}, {}, {}, []

        prices_by_stock, last_prices, warnings = self._init_prices_and_warnings(
            req.stock_ids, req.ticker_map, req.start_date, req.end_date
        )

        current_positions, current_cash, has_cash_tracking = self._calc_initial_cash_and_positions(
            req.trades, req.cash_movements, trade_scope, req.start_date, req.trade_stock_ids
        )

        trades_by_date, cash_by_date = self._group_events_by_date(
            req.trades, req.cash_movements, trade_scope, req.start_date, req.end_date
        )

        portfolio_series, twr_series = self._run_simulation_loop(
            _SimLoopInput(
                start_date=req.start_date,
                end_date=req.end_date,
                has_cash_tracking=has_cash_tracking,
                current_cash=current_cash,
                current_positions=current_positions,
                trades_by_date=trades_by_date,
                cash_by_date=cash_by_date,
                prices_by_stock=prices_by_stock,
                last_prices=last_prices,
                stock_ids=req.stock_ids,
                warnings=warnings,
                ticker_map=req.ticker_map,
            )
        )

        position_values_end = self._calc_ending_position_values(
            req.portfolio, last_prices, req.stock_ids
        )

        return portfolio_series, twr_series, position_values_end, warnings

    def _init_prices_and_warnings(
        self,
        stock_ids: Sequence[int],
        ticker_map: Dict[int, str],
        start_date: date,
        end_date: date,
    ) -> tuple[Dict[int, Dict[date, Decimal]], Dict[int, Decimal | None], List[str]]:
        prices_by_stock: Dict[int, Dict[date, Decimal]] = {
            stock_id: {
                daily.price_date: daily.close_price
                for daily in self._price_repo.get_price_series(stock_id, start_date, end_date)
            }
            for stock_id in stock_ids
        }
        last_prices: Dict[int, Decimal | None] = {}
        warnings: List[str] = []
        for stock_id in stock_ids:
            previous_price = self._price_repo.get_last_price_before(stock_id, start_date)
            last_prices[stock_id] = previous_price.close_price if previous_price else None
        return prices_by_stock, last_prices, warnings

    def _initial_cash_from_history(
        self,
        cash_before: List[CashMovement],
        trades_before: List[Trade],
    ) -> Decimal:
        cash = Decimal("0")
        for cm in cash_before:
            if cm.type == CashMovementType.DEPOSIT:
                cash += cm.amount
            elif cm.type == CashMovementType.WITHDRAW:
                cash -= cm.amount
                if cash < 0:
                    cash = Decimal("0")
        for t in trades_before:
            trade_value = t.quantity * t.price
            if t.side.name == "BUY":
                cash -= trade_value
                if cash < 0:
                    cash = Decimal("0")
            elif t.side.name == "SELL":
                cash += trade_value
        return cash

    def _calc_initial_cash_and_positions(
        self,
        trades: List[Trade],
        cash_movements: List[CashMovement],
        stock_ids: Sequence[int],
        start_date: date,
        trade_stock_ids: Sequence[int] | None = None,
    ) -> tuple[Dict[int, Position], Decimal, bool]:
        trades_before = [t for t in trades if t.trade_date < start_date and t.stock_id in stock_ids]
        cash_before = [cm for cm in cash_movements if cm.movement_date < start_date]
        current_positions = _build_initial_positions(trades_before, stock_ids)
        if trade_stock_ids is not None:
            has_cash_tracking = False
        else:
            has_cash_tracking = len(cash_movements) > 0 or len(cash_before) > 0
        current_cash = self._initial_cash_from_history(cash_before, trades_before) if has_cash_tracking else Decimal("0")
        return current_positions, current_cash, has_cash_tracking

    def _group_events_by_date(
        self,
        trades: List[Trade],
        cash_movements: List[CashMovement],
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> tuple[Dict[date, List[Trade]], Dict[date, List[CashMovement]]]:
        trades_by_date: Dict[date, List[Trade]] = {}
        for trade in trades:
            if trade.stock_id not in stock_ids:
                continue
            if start_date <= trade.trade_date <= end_date:
                trades_by_date.setdefault(trade.trade_date, []).append(trade)

        cash_by_date: Dict[date, List[CashMovement]] = {}
        for cm in cash_movements:
            if start_date <= cm.movement_date <= end_date:
                cash_by_date.setdefault(cm.movement_date, []).append(cm)

        return trades_by_date, cash_by_date

    def _process_cash_tracking_day(
        self,
        current_day: date,
        cash_by_date: Dict[date, List[CashMovement]],
        trades_by_date: Dict[date, List[Trade]],
        current_positions: Dict[int, Position],
        current_cash: Decimal,
    ) -> tuple[Decimal, Decimal]:
        current_cash, daily_net_cash_flow = _apply_cash_movements(
            cash_by_date.get(current_day, []), current_cash
        )
        for trade in sorted(trades_by_date.get(current_day, []), key=_trade_time_key):
            if trade.stock_id in current_positions:
                current_positions[trade.stock_id].apply_trade(trade)
            trade_value = trade.quantity * trade.price
            if trade.side.name == "BUY":
                current_cash -= trade_value
                if current_cash < 0:
                    current_cash = Decimal("0")
            elif trade.side.name == "SELL":
                current_cash += trade_value
        return current_cash, daily_net_cash_flow

    def _process_no_cash_day(
        self,
        current_day: date,
        trades_by_date: Dict[date, List[Trade]],
        current_positions: Dict[int, Position],
    ) -> Decimal:
        daily_net_cash_flow = Decimal("0")
        for trade in sorted(trades_by_date.get(current_day, []), key=_trade_time_key):
            if trade.stock_id in current_positions:
                current_positions[trade.stock_id].apply_trade(trade)
            trade_value = trade.quantity * trade.price
            if trade.side.name == "BUY":
                daily_net_cash_flow += trade_value
            elif trade.side.name == "SELL":
                daily_net_cash_flow -= trade_value
        return daily_net_cash_flow

    def _advance_twr_index(
        self,
        twr_index: Decimal,
        total_value: Decimal,
        previous_total_value,
        daily_net_cash_flow: Decimal,
    ) -> Decimal:
        if previous_total_value is None:
            return twr_index
        base_value = previous_total_value + daily_net_cash_flow
        if base_value > 0:
            twr_index = twr_index * (Decimal("1") + (total_value - base_value) / base_value)
        return twr_index

    def _run_simulation_loop(
        self,
        sim: _SimLoopInput,
    ) -> tuple[Dict[date, Decimal], Dict[date, Decimal]]:
        portfolio_series: Dict[date, Decimal] = {}
        twr_series: Dict[date, Decimal] = {}
        twr_index = Decimal("100")
        previous_total_value: Decimal | None = None
        warned_stocks: set = set()
        current_cash = sim.current_cash
        current_positions = sim.current_positions
        current_day = sim.start_date
        while current_day <= sim.end_date:
            if sim.has_cash_tracking:
                current_cash, daily_net_cash_flow = self._process_cash_tracking_day(
                    current_day, sim.cash_by_date, sim.trades_by_date, current_positions, current_cash
                )
            else:
                daily_net_cash_flow = self._process_no_cash_day(current_day, sim.trades_by_date, current_positions)
            total_value = current_cash
            for stock_id in sim.stock_ids:
                day_price = sim.prices_by_stock[stock_id].get(current_day)
                if day_price is not None:
                    sim.last_prices[stock_id] = day_price
                price = sim.last_prices[stock_id]
                if price is None:
                    if _should_warn_missing_price(current_positions[stock_id], stock_id, warned_stocks):
                        _emit_price_warning(sim.warnings, sim.ticker_map, stock_id, warned_stocks)
                    continue
                total_value += current_positions[stock_id].market_value(price)
            portfolio_series[current_day] = total_value
            twr_index = self._advance_twr_index(twr_index, total_value, previous_total_value, daily_net_cash_flow)
            twr_series[current_day] = twr_index
            previous_total_value = total_value
            current_day += timedelta(days=1)
        return portfolio_series, twr_series

    def _calc_ending_position_values(
        self,
        portfolio: Portfolio,
        last_prices: Dict[int, Decimal | None],
        stock_ids: Sequence[int],
    ) -> Dict[int, Decimal]:
        position_values_end: Dict[int, Decimal] = {}
        for stock_id in stock_ids:
            position = portfolio.positions.get(stock_id)
            if not position or position.total_quantity <= 0:
                continue
            price = last_prices.get(stock_id)
            if price is None:
                continue
            position_values_end[stock_id] = position.market_value(price)
        return position_values_end

    def build_stock_series(
        self,
        stock_ids: Sequence[int],
        ticker_map: Dict[int, str],
        start_date: date,
        end_date: date,
    ) -> tuple[Dict[str, Dict[date, Decimal]], List[str]]:
        series_map: Dict[str, Dict[date, Decimal]] = {}
        warnings: List[str] = []
        for stock_id in stock_ids:
            ticker = ticker_map.get(stock_id)
            if not ticker:
                continue
            points = {
                daily.price_date: daily.close_price
                for daily in self._price_repo.get_price_series(stock_id, start_date, end_date)
            }
            if not points:
                warnings.append(f"{ticker} icin karsilastirma serisi uretilemedi.")
                continue
            series_map[ticker] = points
        return series_map, warnings

    def get_ticker_map(self, stock_ids: Sequence[int]) -> Dict[int, str]:
        return self._stock_repo.get_ticker_map_for_stock_ids(list(stock_ids))

