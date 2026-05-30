from __future__ import annotations

from datetime import date, time as dt_time, timedelta
from typing import List, Tuple

from src.application.services.reporting.daily_history_models import DailyPortfolioSnapshot, DailyPosition
from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely
from src.application.services.simulation.history_position_builder import HistoryPositionBuilder
from src.application.services.simulation.history_simulation_state import SimulationState
from src.application.services.simulation.history_snapshot_builder import HistorySnapshotBuilder
from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.trade import Trade, TradeSide
from src.infrastructure.calendar.bist_holiday_calendar import is_bist_trading_day


class ModelPortfolioHistorySimulationService:
    """Builds dashboard-compatible daily history from model portfolio trades."""

    def __init__(self, model_portfolio_repo, price_repo, stock_repo) -> None:
        self._model_portfolio_repo = model_portfolio_repo
        self._price_repo = price_repo
        self._stock_repo = stock_repo
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

        current_date = start_date
        while current_date <= end_date:
            self._apply_due_trades(state, relevant_trades, current_date)
            is_trading_day = is_bist_trading_day(current_date)
            prices_for_day = price_series.get(current_date, {}) if is_trading_day else {}
            has_prices = bool(prices_for_day)
            total_cost_basis = state.portfolio.total_cost()
            portfolio_value = state.last_portfolio_value if state.last_portfolio_value is not None else None

            if has_prices:
                position_result = self._position_builder.build(
                    current_date=current_date,
                    portfolio=state.portfolio,
                    prices_for_day=prices_for_day,
                    ticker_map=ticker_map,
                    last_close_by_stock=state.last_close_by_stock,
                )
                daily_positions.extend(position_result.positions)
                total_cost_basis = position_result.total_cost_basis
                portfolio_value = position_result.portfolio_value
                state.last_close_by_stock = position_result.last_close_by_stock

            snapshot_result = self._snapshot_builder.build(
                current_date=current_date,
                portfolio_value=portfolio_value,
                total_cost_basis=total_cost_basis,
                last_portfolio_value=state.last_portfolio_value,
                base_portfolio_value=state.base_portfolio_value,
                has_prices=has_prices,
                is_trading_day=is_trading_day,
            )
            daily_snapshots.append(snapshot_result.snapshot)
            state.base_portfolio_value = snapshot_result.base_portfolio_value
            state.last_portfolio_value = snapshot_result.last_portfolio_value
            current_date += timedelta(days=1)

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
