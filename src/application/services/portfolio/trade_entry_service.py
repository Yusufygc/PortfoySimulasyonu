from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide


@dataclass(frozen=True)
class TradeEntryResult:
    trade: Trade
    stock_id: int
    ticker: str


class TradeEntryService:
    def __init__(self, stock_repo, portfolio_service) -> None:
        self._stock_repo = stock_repo
        self._portfolio_service = portfolio_service

    @staticmethod
    def normalize_ticker(ticker: str) -> str:
        normalized = (ticker or "").strip().upper()
        if not normalized:
            raise ValueError("Ticker bos olamaz.")
        if "." not in normalized:
            normalized += ".IS"
        return normalized

    def ensure_stock(self, ticker: str, name: Optional[str] = None, stock_id: Optional[int] = None) -> Stock:
        normalized_ticker = self.normalize_ticker(ticker)
        if stock_id is not None:
            stock = self._stock_repo.get_stock_by_id(stock_id)
            if stock is not None:
                return stock

        stock = self._stock_repo.get_stock_by_ticker(normalized_ticker)
        if stock is not None:
            return stock

        new_stock = Stock(
            id=None,
            ticker=normalized_ticker,
            name=(name or normalized_ticker).strip() or normalized_ticker,
            currency_code="TRY",
        )
        return self._stock_repo.insert_stock(new_stock)

    def submit_trade(
        self,
        ticker: str,
        side: TradeSide | str,
        quantity: int,
        price: Decimal,
        trade_date: date,
        trade_time: Optional[time] = None,
        name: Optional[str] = None,
        stock_id: Optional[int] = None,
    ) -> TradeEntryResult:
        stock = self.ensure_stock(ticker=ticker, name=name, stock_id=stock_id)
        trade_side = side if isinstance(side, TradeSide) else TradeSide(side)
        trade_factory = Trade.create_buy if trade_side == TradeSide.BUY else Trade.create_sell
        saved_trade = self._portfolio_service.add_trade(
            trade_factory(
                stock_id=stock.id,
                trade_date=trade_date,
                trade_time=trade_time or datetime.now().time(),
                quantity=quantity,
                price=price,
            )
        )
        return TradeEntryResult(
            trade=saved_trade,
            stock_id=stock.id,
            ticker=stock.ticker,
        )

