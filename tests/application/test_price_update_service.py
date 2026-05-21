from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.portfolio.price_update_service import PriceUpdateService


def test_update_closing_prices_skips_bist_closed_day():
    price_repo = MagicMock()
    market_client = MagicMock()
    service = PriceUpdateService(price_repo=price_repo, market_data_client=market_client)

    result = service.update_closing_prices_for_stocks(
        price_date=date(2026, 5, 19),
        stock_ticker_map={1: "AAA.IS"},
    )

    assert result.updated_count == 0
    assert result.prices == {}
    assert result.skipped_reason is not None
    market_client.get_closing_prices.assert_not_called()
    price_repo.upsert_daily_prices_bulk.assert_not_called()


def test_update_closing_prices_saves_open_day_prices():
    price_repo = MagicMock()
    market_client = MagicMock()
    market_client.get_closing_prices.return_value = {1: Decimal("12.34")}
    service = PriceUpdateService(price_repo=price_repo, market_data_client=market_client)

    result = service.update_closing_prices_for_stocks(
        price_date=date(2026, 5, 20),
        stock_ticker_map={1: "AAA.IS"},
    )

    assert result.updated_count == 1
    assert result.prices == {1: Decimal("12.34")}
    assert result.skipped_reason is None
    price_repo.upsert_daily_prices_bulk.assert_called_once()
