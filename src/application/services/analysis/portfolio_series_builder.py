from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Sequence

from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.domain.models.trade import Trade
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
        stock_ids: Sequence[int],
        ticker_map: Dict[int, str],
        start_date: date,
        end_date: date,
        portfolio: Portfolio,
    ) -> tuple[Dict[date, Decimal], Dict[int, Decimal], List[str]]:
        if not stock_ids:
            return {}, {}, []

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

        trades_before = [trade for trade in trades if trade.trade_date < start_date and trade.stock_id in stock_ids]
        current_positions = {
            stock_id: Position.from_trades(stock_id, [trade for trade in trades_before if trade.stock_id == stock_id])
            for stock_id in stock_ids
        }
        trades_by_date: Dict[date, List[Trade]] = {}
        for trade in trades:
            if trade.stock_id not in stock_ids:
                continue
            if start_date <= trade.trade_date <= end_date:
                trades_by_date.setdefault(trade.trade_date, []).append(trade)

        portfolio_series: Dict[date, Decimal] = {}
        current_day = start_date
        while current_day <= end_date:
            for trade in sorted(trades_by_date.get(current_day, []), key=lambda item: item.trade_time or time.min):
                current_positions[trade.stock_id].apply_trade(trade)
            total_value = Decimal("0")
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

        position_values_end: Dict[int, Decimal] = {}
        for stock_id in stock_ids:
            position = portfolio.positions.get(stock_id)
            if not position or position.total_quantity <= 0:
                continue
            price = last_prices.get(stock_id)
            if price is None:
                continue
            position_values_end[stock_id] = position.market_value(price)
        return portfolio_series, position_values_end, warnings

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

