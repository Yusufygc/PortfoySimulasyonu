from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List

from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.widgets.shared import Toast
from src.ui.shared.price_utils import build_previous_close_map

logger = logging.getLogger(__name__)


def _compute_portfolio_metrics(positions, price_map: dict, capital: Decimal) -> tuple:
    positions_with_price = [p for p in positions if p.stock_id in price_map]
    positions_value = sum(
        (p.market_value(price_map[p.stock_id]) for p in positions_with_price),
        Decimal("0"),
    )
    total_cost = sum((p.total_cost for p in positions), Decimal("0"))
    profit_loss = sum(
        (p.unrealized_pl(price_map[p.stock_id]) for p in positions_with_price),
        Decimal("0"),
    )
    total_value = positions_value + capital
    return total_value, total_cost, profit_loss


class DashboardPresenter:
    def __init__(self, page) -> None:
        self._page = page

    def load_capital(self) -> None:
        try:
            self._page._capital = self._page.portfolio_service.get_cash_balance()
        except Exception as exc:
            logger.error("Sermaye yuklenemedi: %s", exc, exc_info=True)
            self._page._capital = Decimal("0")

    def refresh_data(self) -> None:
        self.load_capital()
        portfolio: Portfolio = self._page.portfolio_service.get_current_portfolio()
        self._warn_invalid_trades()
        today = date.today()
        snapshot = self._page.return_calc_service.compute_portfolio_value_on(today)

        all_positions: List[Position] = list(portfolio.positions.values())
        positions: List[Position] = [position for position in all_positions if position.total_quantity != 0]
        stock_ids = [position.stock_id for position in positions]
        price_map: Dict[int, Decimal] = dict(snapshot.price_map if snapshot else {})
        price_map.update(self._latest_price_map(stock_ids))
        ticker_map = self._page.stock_repo.get_ticker_map_for_stock_ids(stock_ids)
        previous_close_map = build_previous_close_map(self._page.price_repo, stock_ids, today - timedelta(days=1))

        if self._page.portfolio_model is None:
            self._page.portfolio_model = PortfolioTableModel(
                positions,
                price_map,
                ticker_map,
                previous_close_map=previous_close_map,
                event_bus=self._page.container.event_bus,
                parent=self._page,
            )
            self._page.portfolio_table_widget.set_model(self._page.portfolio_model)
        else:
            self._page.portfolio_model.update_data(positions, price_map, ticker_map, previous_close_map)

        total_value, total_cost, profit_loss = _compute_portfolio_metrics(positions, price_map, self._page._capital)
        self._page.summary_cards.update_base_metrics(total_value, total_cost, self._page._capital, profit_loss)
        self._page.portfolio_table_widget.update_summary_row(total_value, profit_loss)

    def _warn_invalid_trades(self) -> None:
        try:
            invalid_count = len(self._page.portfolio_service.get_portfolio_health().invalid_trades)
        except Exception:
            return
        if invalid_count <= 0:
            self._page._last_invalid_trade_warning_count = 0
            return
        if getattr(self._page, "_last_invalid_trade_warning_count", 0) == invalid_count:
            return
        Toast.warning(
            self._page,
            f"{invalid_count} geçersiz işlem kaydı hesaplamaya dahil edilmedi.",
            duration_ms=5000,
            position="top",
        )
        self._page._last_invalid_trade_warning_count = invalid_count

    def on_prices_updated_event(self, new_prices: Dict[int, Decimal]) -> None:
        if not self._page.portfolio_model or getattr(self._page, "_is_refreshing", False):
            return

        price_map = getattr(self._page.portfolio_model, "_price_map", {})
        price_map.update(new_prices)
        portfolio = self._page.portfolio_service.get_current_portfolio()
        positions = list(portfolio.active_positions.values())
        total_value, total_cost, profit_loss = _compute_portfolio_metrics(positions, price_map, self._page._capital)
        self._page.summary_cards.update_base_metrics(total_value, total_cost, self._page._capital, profit_loss)
        self._page.portfolio_table_widget.update_summary_row(total_value, profit_loss)
        if new_prices and hasattr(self._page, "record_last_update_time"):
            try:
                self._page.record_last_update_time()
            except RuntimeError:
                pass

    def _latest_price_map(self, stock_ids: List[int]) -> Dict[int, Decimal]:
        latest_price_repo = getattr(self._page, "latest_price_repo", None)
        if latest_price_repo is None:
            return {}
        return latest_price_repo.get_latest_price_map(stock_ids)

    def update_returns(self) -> None:
        today = date.today()
        try:
            weekly_rate, _, _ = self._page.return_calc_service.compute_weekly_return(today)
            monthly_rate, _, _ = self._page.return_calc_service.compute_monthly_return(today)
        except Exception as exc:
            logger.error("Getiri hesaplama hatasi: %s", exc, exc_info=True)
            return

        weekly_pct = float(weekly_rate) * 100 if weekly_rate is not None else None
        monthly_pct = float(monthly_rate) * 100 if monthly_rate is not None else None

        self._page._save_returns(weekly_pct, monthly_pct)
        self._page.summary_cards.update_returns(weekly_pct, monthly_pct)
