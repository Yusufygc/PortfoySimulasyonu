from __future__ import annotations

from datetime import date
from typing import List, Optional

from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.trade import Trade
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository

from .models import PortfolioOption


class AnalysisSourceResolver:
    SOURCE_DASHBOARD = "dashboard"
    SOURCE_MODEL_PREFIX = "model:"

    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        stock_repo: IStockRepository,
        model_portfolio_service=None,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._stock_repo = stock_repo
        self._model_portfolio_service = model_portfolio_service

    def get_portfolio_options(self) -> List[PortfolioOption]:
        options = [PortfolioOption(code=self.SOURCE_DASHBOARD, label="Ana Portfoy", kind="dashboard")]
        if self._model_portfolio_service is not None:
            for portfolio in self._model_portfolio_service.get_all_portfolios():
                options.append(
                    PortfolioOption(
                        code=f"{self.SOURCE_MODEL_PREFIX}{portfolio.id}",
                        label=portfolio.name,
                        kind="model",
                    )
                )
        return options

    def get_first_trade_date_for_source(self, source_code: str) -> Optional[date]:
        trades = self.get_source_trades(source_code)
        if not trades:
            return None
        return min(trade.trade_date for trade in trades)

    def get_stock_map_for_source(self, source_code: str) -> dict[int, str]:
        trades = self.get_source_trades(source_code)
        stock_ids = sorted({trade.stock_id for trade in trades})
        return self._stock_repo.get_ticker_map_for_stock_ids(stock_ids)

    def get_source_trades(self, source_code: str) -> List[Trade]:
        if source_code == self.SOURCE_DASHBOARD:
            return list(self._portfolio_repo.get_all_trades())
        if source_code.startswith(self.SOURCE_MODEL_PREFIX) and self._model_portfolio_service is not None:
            portfolio_id = int(source_code.split(":", 1)[1])
            model_trades = self._model_portfolio_service.get_portfolio_trades(portfolio_id)
            converted: List[Trade] = []
            for trade in model_trades:
                factory = Trade.create_buy if trade.side == ModelTradeSide.BUY else Trade.create_sell
                converted.append(
                    factory(
                        stock_id=trade.stock_id,
                        trade_date=trade.trade_date,
                        quantity=trade.quantity,
                        price=trade.price,
                        trade_time=trade.trade_time,
                    )
                )
            return converted
        return []

    def get_source_label(self, source_code: str) -> str:
        for option in self.get_portfolio_options():
            if option.code == source_code:
                return option.label
        return "Portfoy"

