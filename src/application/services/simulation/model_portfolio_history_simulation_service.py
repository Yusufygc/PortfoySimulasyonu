from __future__ import annotations

from datetime import date, time as dt_time, timedelta
from typing import List, NamedTuple, Tuple

from src.application.services.market.trading_calendar import MarketTradingCalendar, WeekdayTradingCalendar
from src.application.services.reporting.daily_history_models import DailyPortfolioSnapshot, DailyPosition
from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely
from src.application.services.simulation.history_position_builder import HistoryPositionBuilder
from src.application.services.simulation.history_simulation_state import SimulationState
from src.application.services.simulation.history_snapshot_builder import HistorySnapshotBuilder, SnapshotValuation
from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.trade import Trade, TradeSide


class _SimDayCtx(NamedTuple):
    relevant_trades: list
    price_series: dict
    ticker_map: "dict[int, str]"


class ModelPortfolioHistorySimulationService:
    """Builds dashboard-compatible daily history from model portfolio trades."""

    def __init__(
        self,
        model_portfolio_repo,
        price_repo,
        stock_repo,
        trading_calendar: MarketTradingCalendar | None = None,
    ) -> None:
        self._model_portfolio_repo = model_portfolio_repo
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._trading_calendar = trading_calendar or WeekdayTradingCalendar()
        self._position_builder = HistoryPositionBuilder()
        self._snapshot_builder = HistorySnapshotBuilder()

    def simulate_history(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date,
    ) -> Tuple[List[DailyPosition], List[DailyPortfolioSnapshot]]:
        start_date, end_date = self._normalized_range(start_date, end_date)
        relevant_trades = self._sorted_relevant_trades(portfolio_id, end_date)
        if not relevant_trades:
            return [], []

        stock_ids = sorted({trade.stock_id for trade in relevant_trades})
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids) if stock_ids else []
        ticker_map = {stock.id: stock.ticker for stock in stocks if stock.id is not None}
        price_series = self._price_repo.get_portfolio_value_series(
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
        )

        state = SimulationState()
        daily_positions: list[DailyPosition] = []
        daily_snapshots: list[DailyPortfolioSnapshot] = []
        ctx = _SimDayCtx(relevant_trades=relevant_trades, price_series=price_series, ticker_map=ticker_map)
        for current_date in self._date_range(start_date, end_date):
            self._simulate_day(current_date, state, ctx, daily_positions, daily_snapshots)

        return daily_positions, daily_snapshots

    def _sorted_relevant_trades(self, portfolio_id: int, end_date: date) -> list[Trade]:
        model_trades = [
            trade
            for trade in self._model_portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
            if trade.trade_date <= end_date
        ]
        model_trades.sort(
            key=lambda trade: (
                trade.trade_date,
                getattr(trade, "trade_time", None) or dt_time.min,
                getattr(trade, "id", None) or 0,
            )
        )
        return build_portfolio_safely([self._to_portfolio_trade(trade) for trade in model_trades]).valid_trades

    @staticmethod
    def _normalized_range(start_date: date, end_date: date) -> tuple[date, date]:
        if end_date < start_date:
            return end_date, start_date
        return start_date, end_date

    @staticmethod
    def _to_portfolio_trade(model_trade) -> Trade:
        side = TradeSide.BUY if model_trade.side == ModelTradeSide.BUY else TradeSide.SELL
        return Trade(
            id=model_trade.id,
            stock_id=model_trade.stock_id,
            trade_date=model_trade.trade_date,
            trade_time=model_trade.trade_time,
            side=side,
            quantity=model_trade.quantity,
            price=model_trade.price,
        )

    @staticmethod
    def _apply_due_trades(state: SimulationState, relevant_trades: list[Trade], current_date: date) -> None:
        trade_count = len(relevant_trades)
        while state.trade_cursor < trade_count and relevant_trades[state.trade_cursor].trade_date <= current_date:
            state.portfolio.apply_trade(relevant_trades[state.trade_cursor])
            state.trade_cursor += 1

    def _simulate_day(
        self,
        current_date: date,
        state: SimulationState,
        ctx: "_SimDayCtx",
        daily_positions: list,
        daily_snapshots: list,
    ) -> None:
        self._apply_due_trades(state, ctx.relevant_trades, current_date)
        is_trading_day = self._trading_calendar.is_trading_day(current_date)
        prices_for_day = ctx.price_series.get(current_date, {}) if is_trading_day else {}
        position_result = self._build_positions_for_day(current_date, state, prices_for_day, ctx.ticker_map)
        if position_result is not None:
            daily_positions.extend(position_result.positions)
            total_cost_basis = position_result.total_cost_basis
            portfolio_value = position_result.portfolio_value
            state.last_close_by_stock = position_result.last_close_by_stock
        else:
            total_cost_basis = state.portfolio.total_cost()
            portfolio_value = state.last_portfolio_value if state.last_portfolio_value is not None else None

        snapshot_result = self._snapshot_builder.build(
            current_date=current_date,
            val=SnapshotValuation(
                portfolio_value=portfolio_value,
                total_cost_basis=total_cost_basis,
                last_portfolio_value=state.last_portfolio_value,
                base_portfolio_value=state.base_portfolio_value,
            ),
            has_prices=bool(prices_for_day),
            is_trading_day=is_trading_day,
        )
        daily_snapshots.append(snapshot_result.snapshot)
        state.base_portfolio_value = snapshot_result.base_portfolio_value
        state.last_portfolio_value = snapshot_result.last_portfolio_value

    def _build_positions_for_day(
        self,
        current_date: date,
        state: SimulationState,
        prices_for_day: dict,
        ticker_map: dict[int, str],
    ):
        if not prices_for_day:
            return None
        return self._position_builder.build(
            current_date=current_date,
            portfolio=state.portfolio,
            prices_for_day=prices_for_day,
            ticker_map=ticker_map,
            last_close_by_stock=state.last_close_by_stock,
        )

    @staticmethod
    def _date_range(start_date: date, end_date: date):
        current_date = start_date
        while current_date <= end_date:
            yield current_date
            current_date += timedelta(days=1)
