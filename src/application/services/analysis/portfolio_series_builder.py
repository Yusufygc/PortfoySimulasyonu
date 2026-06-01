from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Sequence

from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.models.trade import Trade
from src.domain.models.trade import Trade
from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository


class PortfolioSeriesBuilder:
    def __init__(
        self,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
    ) -> None:
        self._price_repo = price_repo
        self._stock_repo = stock_repo

    def resolve_stock_scope(self, trades: Iterable[Trade], selected_stock_ids: Sequence[int]) -> List[int]:
        selected = [stock_id for stock_id in selected_stock_ids if stock_id]
        if selected:
            return sorted(set(selected))
        return sorted({trade.stock_id for trade in trades})

    def compute_portfolio_series(
        self,
        trades: List[Trade],
        cash_movements: List[CashMovement],
        stock_ids: Sequence[int],
        ticker_map: Dict[int, str],
        start_date: date,
        end_date: date,
        portfolio: Portfolio,
    ) -> tuple[Dict[date, Decimal], Dict[int, Decimal], List[str]]:
        if not stock_ids:
            return {}, {}, []

        prices_by_stock, last_prices, warnings = self._init_prices_and_warnings(
            stock_ids, ticker_map, start_date, end_date
        )

        current_positions, current_cash, has_cash_tracking = self._calc_initial_cash_and_positions(
            trades, cash_movements, stock_ids, start_date
        )

        trades_by_date, cash_by_date = self._group_events_by_date(
            trades, cash_movements, stock_ids, start_date, end_date
        )

        portfolio_series = self._run_simulation_loop(
            start_date,
            end_date,
            has_cash_tracking,
            current_cash,
            current_positions,
            trades_by_date,
            cash_by_date,
            prices_by_stock,
            last_prices,
            stock_ids,
        )

        position_values_end = self._calc_ending_position_values(
            portfolio, last_prices, stock_ids
        )

        return portfolio_series, position_values_end, warnings

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
            if not prices_by_stock[stock_id]:
                warnings.append(f"{ticker_map.get(stock_id, str(stock_id))} icin tarih araliginda fiyat verisi bulunamadi.")
        return prices_by_stock, last_prices, warnings

    def _calc_initial_cash_and_positions(
        self,
        trades: List[Trade],
        cash_movements: List[CashMovement],
        stock_ids: Sequence[int],
        start_date: date,
    ) -> tuple[Dict[int, Position], Decimal, bool]:
        trades_before = [trade for trade in trades if trade.trade_date < start_date and trade.stock_id in stock_ids]
        cash_before = [cm for cm in cash_movements if cm.movement_date < start_date]

        current_positions = {
            stock_id: Position.from_trades(stock_id, [trade for trade in trades_before if trade.stock_id == stock_id])
            for stock_id in stock_ids
        }

        has_cash_tracking = len(cash_movements) > 0 or len(cash_before) > 0
        current_cash = Decimal("0")

        if has_cash_tracking:
            for cm in cash_before:
                if cm.type == CashMovementType.DEPOSIT:
                    current_cash += cm.amount
                elif cm.type == CashMovementType.WITHDRAW:
                    current_cash -= cm.amount

            for t in trades_before:
                trade_value = t.quantity * t.price
                if t.side.name == "BUY":
                    current_cash -= trade_value
                elif t.side.name == "SELL":
                    current_cash += trade_value

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

    def _run_simulation_loop(
        self,
        start_date: date,
        end_date: date,
        has_cash_tracking: bool,
        current_cash: Decimal,
        current_positions: Dict[int, Position],
        trades_by_date: Dict[date, List[Trade]],
        cash_by_date: Dict[date, List[CashMovement]],
        prices_by_stock: Dict[int, Dict[date, Decimal]],
        last_prices: Dict[int, Decimal | None],
        stock_ids: Sequence[int],
    ) -> Dict[date, Decimal]:
        portfolio_series: Dict[date, Decimal] = {}
        current_day = start_date
        while current_day <= end_date:
            if has_cash_tracking:
                # Gunluk nakit hareketlerini isle
                for cm in sorted(cash_by_date.get(current_day, []), key=lambda item: item.movement_time or time.min):
                    if cm.type == CashMovementType.DEPOSIT:
                        current_cash += cm.amount
                    elif cm.type == CashMovementType.WITHDRAW:
                        current_cash -= cm.amount

                # Gunluk hisse islemlerini isle
                for trade in sorted(trades_by_date.get(current_day, []), key=lambda item: item.trade_time or time.min):
                    current_positions[trade.stock_id].apply_trade(trade)
                    trade_value = trade.quantity * trade.price
                    if trade.side.name == "BUY":
                        current_cash -= trade_value
                    elif trade.side.name == "SELL":
                        current_cash += trade_value
            else:
                # Sadece hisse pozisyonlarini guncelle, nakit 0 kalir
                for trade in sorted(trades_by_date.get(current_day, []), key=lambda item: item.trade_time or time.min):
                    current_positions[trade.stock_id].apply_trade(trade)

            total_value = current_cash
            for stock_id in stock_ids:
                day_price = prices_by_stock[stock_id].get(current_day)
                if day_price is not None:
                    last_prices[stock_id] = day_price
                price = last_prices[stock_id]
                if price is None:
                    continue
                total_value += current_positions[stock_id].market_value(price)
            portfolio_series[current_day] = total_value
            current_day += timedelta(days=1)
        return portfolio_series

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

