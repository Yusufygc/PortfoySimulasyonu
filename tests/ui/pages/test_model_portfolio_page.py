from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

from src.ui.pages.model_portfolio_page import ModelPortfolioPage


class DummyModelPortfolioService:
    def get_positions_with_details(self, portfolio_id):
        return [{"stock_id": 2, "ticker": "BBB.IS"}]


class DummyPriceRepo:
    def __init__(self):
        self.saved_prices = []

    def upsert_daily_prices_bulk(self, prices):
        self.saved_prices.extend(prices)


class DummyEventSignal:
    def __init__(self):
        self.emitted = []

    def emit(self, payload):
        self.emitted.append(payload)


def test_model_portfolio_refresh_persists_prices_to_daily_prices():
    price_repo = DummyPriceRepo()
    event_signal = DummyEventSignal()
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.current_portfolio_id = 4
    page.model_portfolio_service = DummyModelPortfolioService()
    page.price_repo = price_repo
    page.current_price_map = {}
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=event_signal))
    page.price_lookup_func = lambda ticker: SimpleNamespace(
        price=Decimal("22.50"),
        as_of=datetime(2026, 4, 28, 12, 0),
        source="intraday",
    )
    page._update_view = lambda: None
    page.record_last_update_time = lambda: None
    page.show_last_update_toast_once = lambda **kwargs: None

    ModelPortfolioPage._on_refresh_prices(page)

    assert page.current_price_map == {2: Decimal("22.50")}
    assert len(price_repo.saved_prices) == 1
    assert price_repo.saved_prices[0].stock_id == 2
    assert price_repo.saved_prices[0].close_price == Decimal("22.50")
    assert event_signal.emitted == [{2: Decimal("22.50")}]
