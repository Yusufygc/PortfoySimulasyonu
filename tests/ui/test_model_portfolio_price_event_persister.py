from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from src.ui.pages.model_portfolio.utils.portfolio_price_event_persister import (
    ModelPortfolioPriceEventPersister,
)


class FakeModelPortfolioService:
    def __init__(self):
        self.portfolios = [
            SimpleNamespace(id=4, name="model-a"),
            SimpleNamespace(id=5, name="model-b"),
            SimpleNamespace(id=None, name="unsaved"),
        ]
        self.positions = {
            4: {1: 100, 2: 50},
            5: {2: 10, 3: 20},
        }

    def get_all_portfolios(self):
        return list(self.portfolios)

    def get_positions(self, portfolio_id):
        return dict(self.positions.get(portfolio_id, {}))


class FakeSettingsManager:
    def __init__(self):
        self.maps = {
            4: {1: Decimal("9.50")},
            5: {3: Decimal("29.00")},
        }
        self.saved = []

    def load_saved_price_map(self, portfolio_id):
        return dict(self.maps.get(portfolio_id, {}))

    def save_portfolio_prices_and_time(self, portfolio_id, price_map, updated_at):
        self.maps[portfolio_id] = dict(price_map)
        self.saved.append((portfolio_id, dict(price_map), updated_at))


def test_model_portfolio_price_event_persister_merges_prices_for_all_affected_portfolios():
    updated_at = datetime(2026, 6, 5, 18, 30)
    settings = FakeSettingsManager()
    persister = ModelPortfolioPriceEventPersister(
        FakeModelPortfolioService(),
        settings_manager=settings,
        clock=lambda: updated_at,
    )

    updated_count = persister.on_prices_updated(
        {
            2: Decimal("22.75"),
            3: Decimal("31.40"),
            99: Decimal("99.99"),
        }
    )

    assert updated_count == 2
    assert settings.maps[4] == {1: Decimal("9.50"), 2: Decimal("22.75")}
    assert settings.maps[5] == {2: Decimal("22.75"), 3: Decimal("31.40")}
    assert settings.saved == [
        (4, {1: Decimal("9.50"), 2: Decimal("22.75")}, updated_at),
        (5, {2: Decimal("22.75"), 3: Decimal("31.40")}, updated_at),
    ]


def test_model_portfolio_price_event_persister_skips_unrelated_prices():
    settings = FakeSettingsManager()
    persister = ModelPortfolioPriceEventPersister(
        FakeModelPortfolioService(),
        settings_manager=settings,
        clock=lambda: datetime(2026, 6, 5, 18, 30),
    )

    updated_count = persister.on_prices_updated({99: Decimal("99.99")})

    assert updated_count == 0
    assert settings.saved == []
    assert settings.maps == {
        4: {1: Decimal("9.50")},
        5: {3: Decimal("29.00")},
    }
