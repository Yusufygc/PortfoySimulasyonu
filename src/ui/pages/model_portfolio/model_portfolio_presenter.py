from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Optional, TYPE_CHECKING

from src.ui.shared.locale_tr import L10N
from src.ui.shared.price_utils import build_previous_close_map

if TYPE_CHECKING:
    from src.ui.pages.model_portfolio.model_portfolio_page import ModelPortfolioPage

logger = logging.getLogger(__name__)

class ModelPortfolioPresenter:
    def __init__(self, page: ModelPortfolioPage) -> None:
        self._page = page

    def update_view(self) -> None:
        if self._page.current_portfolio_id is None:
            return

        summary = self._page.model_portfolio_service.get_portfolio_summary(
            self._page.current_portfolio_id,
            self._page.current_price_map,
        )
        self._page.card_initial.set_value(f"TL {summary.get('net_capital', summary['initial_cash']):,.2f}")
        self._page.card_cash.set_value(f"TL {summary['remaining_cash']:,.2f}")
        self._page.card_value.set_value(f"TL {summary['total_value']:,.2f}")

        profit_loss = round(summary["profit_loss"], 2)
        if profit_loss == 0:
            self._page.card_pl.set_value(L10N.TL_000)
            self._page.card_pl.set_value_state("neutral")
        else:
            self._page.card_pl.set_value(f"TL {profit_loss:+,.2f}")
            self._page.card_pl.set_value_state("positive" if profit_loss > 0 else "negative")

        positions = self._page.model_portfolio_service.get_positions_with_details(
            self._page.current_portfolio_id,
            self._page.current_price_map,
        )
        
        stock_ids = [pos.get("stock_id") for pos in positions if pos.get("stock_id") is not None]
        previous_close_map = build_previous_close_map(self._page.price_repo, stock_ids, date.today())
        
        self._page.positions_table.populate(positions, previous_close_map=previous_close_map)
        self._page.positions_stack.setCurrentWidget(
            self._page.empty_positions_state if not positions else self._page.positions_table
        )

    def load_current_price_map(self, portfolio_id: int) -> Dict[int, Decimal]:
        get_positions = getattr(self._page.model_portfolio_service, "get_positions", None)
        if get_positions is None:
            return {}
        positions = get_positions(portfolio_id)
        stock_ids = sorted(positions)
        price_map: Dict[int, Decimal] = {}

        latest_price_repo = getattr(self._page, "latest_price_repo", None)
        if latest_price_repo is not None:
            price_map.update(latest_price_repo.get_latest_price_map(stock_ids))

        missing_ids = [stock_id for stock_id in stock_ids if stock_id not in price_map]
        for stock_id in missing_ids:
            daily_price = self._page.price_repo.get_last_price_before(stock_id, date.today())
            if daily_price is not None:
                price_map[stock_id] = daily_price.close_price
        return price_map

    def on_prices_updated_event(self, prices: Dict[int, Decimal]) -> None:
        if self._page.current_portfolio_id is None or not prices:
            return
            
        positions = self._page.model_portfolio_service.get_positions(self._page.current_portfolio_id)
        relevant_prices = {
            stock_id: price
            for stock_id, price in prices.items()
            if stock_id in positions
        }
        if not relevant_prices:
            return
            
        self._page.current_price_map.update(relevant_prices)
        self.update_view()
        
        try:
            self._page.record_last_update_time()
        except RuntimeError:
            pass
