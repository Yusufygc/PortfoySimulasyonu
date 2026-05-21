from __future__ import annotations

from datetime import date, time as dt_time, timedelta
from decimal import Decimal
from typing import List, Tuple

from src.application.services.reporting.daily_history_models import DailyPortfolioSnapshot, DailyPosition
from src.application.services.simulation.history_position_builder import HistoryPositionBuilder
from src.application.services.simulation.history_simulation_state import SimulationState
from src.application.services.simulation.history_snapshot_builder import HistorySnapshotBuilder
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository


class HistorySimulationService:
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._position_builder = HistoryPositionBuilder()
        self._snapshot_builder = HistorySnapshotBuilder()

    def simulate_history(
        self,
        start_date: date,
        end_date: date,
    ) -> Tuple[List[DailyPosition], List[DailyPortfolioSnapshot]]:
        start_date, end_date = self._normalized_range(start_date, end_date)
        relevant_trades = self._sorted_relevant_trades(end_date)
        if not relevant_trades:
            return [], []

        stocks = self._stock_repo.get_all_stocks()
        ticker_map = {stock.id: stock.ticker for stock in stocks}
        stock_ids = [stock.id for stock in stocks]
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
            prices_for_day = price_series.get(current_date, {})
            has_prices = bool(prices_for_day)
            total_cost_basis = Decimal("0")
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
                is_weekend=current_date.weekday() >= 5,
            )
            daily_snapshots.append(snapshot_result.snapshot)
            state.base_portfolio_value = snapshot_result.base_portfolio_value
            state.last_portfolio_value = snapshot_result.last_portfolio_value
            current_date += timedelta(days=1)

        return daily_positions, daily_snapshots

    def _normalized_range(self, start_date: date, end_date: date) -> tuple[date, date]:
        if end_date < start_date:
            return end_date, start_date
        return start_date, end_date

    def _sorted_relevant_trades(self, end_date: date):
        relevant_trades = [
            trade
            for trade in self._portfolio_repo.get_all_trades()
            if trade.trade_date <= end_date
        ]
        relevant_trades.sort(
            key=lambda trade: (
                trade.trade_date,
                getattr(trade, "trade_time", None) or dt_time.min,
                getattr(trade, "id", None) or 0,
            )
        )
        return relevant_trades

    def _apply_due_trades(self, state: SimulationState, relevant_trades: list, current_date: date) -> None:
        trade_count = len(relevant_trades)
        while state.trade_cursor < trade_count and relevant_trades[state.trade_cursor].trade_date <= current_date:
            state.portfolio.apply_trade(relevant_trades[state.trade_cursor])
            state.trade_cursor += 1
