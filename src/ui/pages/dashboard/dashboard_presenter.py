from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List

from src.domain.models.portfolio import Portfolio
from src.domain.models.position import Position
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.widgets.shared import Toast

logger = logging.getLogger(__name__)


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
        price_map: Dict[int, Decimal] = snapshot.price_map if snapshot else {}
        stock_ids = [position.stock_id for position in positions]
        ticker_map = self._page.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        if self._page.portfolio_model is None:
            self._page.portfolio_model = PortfolioTableModel(
                positions,
                price_map,
                ticker_map,
                event_bus=self._page.container.event_bus,
                parent=self._page,
            )
            self._page.portfolio_table_widget.set_model(self._page.portfolio_model)
        else:
            self._page.portfolio_model.update_data(positions, price_map, ticker_map)

        positions_value = snapshot.total_value if snapshot else Decimal("0")
        total_value = positions_value + self._page._capital
        total_cost = sum(position.total_cost for position in positions)
        profit_loss = snapshot.total_unrealized_pl if snapshot else Decimal("0")

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
        active_positions = portfolio.active_positions
        total_cost = sum((position.total_cost for position in active_positions.values()), Decimal("0"))
        positions_value = sum(
            (
                position.market_value(price_map[position.stock_id])
                for position in active_positions.values()
                if position.stock_id in price_map
            ),
            Decimal("0"),
        )
        total_value = positions_value + self._page._capital
        profit_loss = sum(
            (
                position.unrealized_pl(price_map[position.stock_id])
                for position in active_positions.values()
                if position.stock_id in price_map
            ),
            Decimal("0"),
        )
        self._page.summary_cards.update_base_metrics(total_value, total_cost, self._page._capital, profit_loss)
        self._page.portfolio_table_widget.update_summary_row(total_value, profit_loss)
        if new_prices and hasattr(self._page, "record_last_update_time"):
            try:
                self._page.record_last_update_time()
            except RuntimeError:
                pass

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
