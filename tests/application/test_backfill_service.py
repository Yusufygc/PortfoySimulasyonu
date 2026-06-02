"""BackfillService unit testleri."""
from __future__ import annotations

import pytest

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.simulation.backfill_service import BackfillService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock


# ────── Yardımcı fabrikalar ──────────────────────────────────────────────────

def _make_stock(ticker: str, stock_id: int = 1) -> Stock:
    return Stock(id=stock_id, ticker=ticker, name=ticker, currency_code="TRY")


class FakeMarketDataClient:
    def __init__(self, series_by_ticker=None):
        self.series_by_ticker = series_by_ticker or {}
        self.series_requests = []

    def get_closing_price(self, stock_id: int, ticker: str, price_date: date):
        raise NotImplementedError

    def get_closing_prices(self, stock_ids, tickers, price_date):
        raise NotImplementedError

    def get_price_series(self, ticker: str, start_date: date, end_date: date):
        self.series_requests.append((ticker, start_date, end_date))
        return self.series_by_ticker.get(ticker, {})


def _make_service(stocks=None, series_by_ticker=None):
    stock_repo = MagicMock()
    stock_repo.get_all_stocks.return_value = stocks or []

    price_repo = MagicMock()
    price_repo.upsert_daily_prices_bulk.return_value = None

    market_client = FakeMarketDataClient(series_by_ticker=series_by_ticker)
    service = BackfillService(
        stock_repo=stock_repo,
        price_repo=price_repo,
        market_data_client=market_client,
    )

    return service, stock_repo, price_repo, market_client


# ────── backfill_range ───────────────────────────────────────────────────────

def test_backfill_range_raises_if_start_after_end():
    svc, _, _, _ = _make_service()
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        svc.backfill_range(date(2026, 2, 1), date(2026, 1, 1))


def test_backfill_range_raises_if_no_stocks():
    svc, _, _, _ = _make_service(stocks=[])
    with pytest.raises(ValueError, match="kayıtlı hisse"):
        svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))


def test_backfill_range_returns_zero_on_empty_series():
    stock = _make_stock("MERKO.IS")
    svc, _, price_repo, market_client = _make_service(stocks=[stock])

    count = svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))

    assert count == 0
    price_repo.upsert_daily_prices_bulk.assert_not_called()
    assert market_client.series_requests == [("MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))]


def test_backfill_range_saves_prices_for_single_ticker():
    stock = _make_stock("MERKO.IS", stock_id=7)
    svc, _, price_repo, _ = _make_service(
        stocks=[stock],
        series_by_ticker={
            "MERKO.IS": {
                date(2026, 1, 2): Decimal("10.5"),
                date(2026, 1, 5): Decimal("11.0"),
            }
        },
    )

    count = svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))

    assert count == 2
    saved: list[DailyPrice] = price_repo.upsert_daily_prices_bulk.call_args[0][0]
    assert saved[0].stock_id == 7
    assert saved[0].close_price == Decimal("10.5")
    assert saved[1].close_price == Decimal("11.0")


# ────── backfill_for_single_stock ────────────────────────────────────────────

def test_backfill_for_single_stock_raises_if_start_after_end():
    svc, _, _, _ = _make_service()
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 2, 1), date(2026, 1, 1))


def test_backfill_for_single_stock_returns_zero_on_empty():
    svc, _, price_repo, _ = _make_service()
    count = svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))
    assert count == 0
    price_repo.upsert_daily_prices_bulk.assert_not_called()


def test_backfill_for_single_stock_saves_price_series():
    svc, _, price_repo, market_client = _make_service(
        series_by_ticker={
            "MERKO.IS": {
                date(2026, 1, 2): Decimal("15.0"),
                date(2026, 1, 5): Decimal("16.25"),
            }
        }
    )

    count = svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))

    assert count == 2
    saved = price_repo.upsert_daily_prices_bulk.call_args[0][0]
    assert saved[0].close_price == Decimal("15.0")
    assert saved[1].close_price == Decimal("16.25")
    assert market_client.series_requests == [("MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))]


# ────── delete_range ─────────────────────────────────────────────────────────

def test_delete_range_raises_if_start_after_end():
    svc, _, _, _ = _make_service()
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        svc.delete_range(date(2026, 2, 1), date(2026, 1, 1))


def test_delete_range_delegates_to_repo():
    svc, _, price_repo, _ = _make_service()
    price_repo.delete_prices_in_range.return_value = 42

    result = svc.delete_range(date(2026, 1, 1), date(2026, 1, 31))

    assert result == 42
    price_repo.delete_prices_in_range.assert_called_once_with(date(2026, 1, 1), date(2026, 1, 31))
