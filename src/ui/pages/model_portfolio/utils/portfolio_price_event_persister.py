from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable, Mapping

from src.ui.pages.model_portfolio.utils.portfolio_settings import PortfolioSettingsManager

logger = logging.getLogger(__name__)


class ModelPortfolioPriceEventPersister:
    def __init__(
        self,
        model_portfolio_service,
        settings_manager: PortfolioSettingsManager | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._model_portfolio_service = model_portfolio_service
        self._settings_manager = settings_manager or PortfolioSettingsManager()
        self._clock = clock or datetime.now

    def on_prices_updated(self, prices: Mapping[int, Decimal] | None) -> int:
        if not prices:
            return 0

        updated_portfolios = 0
        updated_at = self._clock()
        for portfolio in self._model_portfolio_service.get_all_portfolios():
            portfolio_id = getattr(portfolio, "id", None)
            if portfolio_id is None:
                continue
            try:
                positions = self._model_portfolio_service.get_positions(portfolio_id)
            except Exception as exc:
                logger.warning("Model portfolio positions could not be read for %s: %s", portfolio_id, exc)
                continue

            relevant_prices = {
                stock_id: price
                for stock_id, price in prices.items()
                if stock_id in positions
            }
            if not relevant_prices:
                continue

            saved_price_map = self._settings_manager.load_saved_price_map(portfolio_id)
            saved_price_map.update(relevant_prices)
            self._settings_manager.save_portfolio_prices_and_time(
                portfolio_id,
                saved_price_map,
                updated_at,
            )
            updated_portfolios += 1

        return updated_portfolios
