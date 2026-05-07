"""BackfillService unit testleri (yfinance mock'lu)."""
from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.application.services.simulation.backfill_service import BackfillService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock


# ────── Yardımcı fabrikalar ──────────────────────────────────────────────────

def _make_stock(ticker: str, stock_id: int = 1) -> Stock:
    return Stock(id=stock_id, ticker=ticker, name=ticker, currency_code="TRY")


def _make_service(stocks=None, saved_prices=None):
    stock_repo = MagicMock()
    stock_repo.get_all_stocks.return_value = stocks or []

    price_repo = MagicMock()
    price_repo.upsert_daily_prices_bulk.return_value = None

    return BackfillService(stock_repo=stock_repo, price_repo=price_repo), stock_repo, price_repo


# ────── backfill_range ───────────────────────────────────────────────────────

def test_backfill_range_raises_if_start_after_end():
    svc, _, _ = _make_service()
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        svc.backfill_range(date(2026, 2, 1), date(2026, 1, 1))


def test_backfill_range_raises_if_no_stocks():
    svc, _, _ = _make_service(stocks=[])
    with pytest.raises(ValueError, match="kayıtlı hisse"):
        svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))


def test_backfill_range_returns_zero_on_empty_df():
    stock = _make_stock("MERKO.IS")
    svc, _, price_repo = _make_service(stocks=[stock])

    with patch("yfinance.download", return_value=pd.DataFrame()):
        count = svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))

    assert count == 0
    price_repo.upsert_daily_prices_bulk.assert_not_called()


def test_backfill_range_uses_auto_adjust_true():
    """auto_adjust=True olduğu doğrulanır."""
    stock = _make_stock("MERKO.IS")
    svc, _, _ = _make_service(stocks=[stock])

    with patch("yfinance.download", return_value=pd.DataFrame()) as mock_dl:
        svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))

    _, kwargs = mock_dl.call_args
    assert kwargs.get("auto_adjust") is True


def test_backfill_range_saves_prices_for_single_ticker():
    stock = _make_stock("MERKO.IS", stock_id=7)
    svc, _, price_repo = _make_service(stocks=[stock])

    idx = pd.to_datetime(["2026-01-02", "2026-01-05"])
    # Tek ticker → flat DataFrame (no MultiIndex)
    df = pd.DataFrame({"Close": [10.5, 11.0]}, index=idx)
    df.index.name = "Date"

    with patch("yfinance.download", return_value=df):
        count = svc.backfill_range(date(2026, 1, 1), date(2026, 1, 5))

    assert count == 2
    saved: list[DailyPrice] = price_repo.upsert_daily_prices_bulk.call_args[0][0]
    assert saved[0].stock_id == 7
    assert saved[0].close_price == pytest.approx(10.5)
    assert saved[1].close_price == pytest.approx(11.0)


# ────── backfill_for_single_stock ────────────────────────────────────────────

def test_backfill_for_single_stock_raises_if_start_after_end():
    svc, _, _ = _make_service()
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 2, 1), date(2026, 1, 1))


def test_backfill_for_single_stock_returns_zero_on_empty():
    svc, _, price_repo = _make_service()
    with patch("yfinance.download", return_value=pd.DataFrame()):
        count = svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))
    assert count == 0
    price_repo.upsert_daily_prices_bulk.assert_not_called()


def test_backfill_for_single_stock_uses_auto_adjust_true():
    svc, _, _ = _make_service()
    with patch("yfinance.download", return_value=pd.DataFrame()) as mock_dl:
        svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))
    _, kwargs = mock_dl.call_args
    assert kwargs.get("auto_adjust") is True


def test_backfill_for_single_stock_skips_nan_rows():
    svc, _, price_repo = _make_service()
    import numpy as np
    idx = pd.to_datetime(["2026-01-02", "2026-01-05"])
    df = pd.DataFrame({"Close": [float("nan"), 15.0]}, index=idx)

    with patch("yfinance.download", return_value=df):
        count = svc.backfill_for_single_stock(1, "MERKO.IS", date(2026, 1, 1), date(2026, 1, 5))

    assert count == 1
    saved = price_repo.upsert_daily_prices_bulk.call_args[0][0]
    assert saved[0].close_price == pytest.approx(15.0)


# ────── delete_range ─────────────────────────────────────────────────────────

def test_delete_range_raises_if_start_after_end():
    svc, _, _ = _make_service()
    with pytest.raises(ValueError, match="Başlangıç tarihi"):
        svc.delete_range(date(2026, 2, 1), date(2026, 1, 1))


def test_delete_range_delegates_to_repo():
    svc, _, price_repo = _make_service()
    price_repo.delete_prices_in_range.return_value = 42

    result = svc.delete_range(date(2026, 1, 1), date(2026, 1, 31))

    assert result == 42
    price_repo.delete_prices_in_range.assert_called_once_with(date(2026, 1, 1), date(2026, 1, 31))
