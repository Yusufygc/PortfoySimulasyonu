"""DCABacktestService orkestrasyon testleri (mock repo)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.simulation.dca_backtest_service import DCABacktestService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock


def _stock(id_: int, ticker: str) -> Stock:
    return Stock(id=id_, ticker=ticker, name=ticker, currency_code="TRY")


def _rows(stock_id: int, prices: dict[date, float]) -> list[DailyPrice]:
    return [
        DailyPrice(id=None, stock_id=stock_id, price_date=d, close_price=Decimal(str(p)))
        for d, p in prices.items()
    ]


class TestRun:
    def test_single_ticker_equal_weight_default(self):
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = _stock(1, "AKBNK")
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, {
            date(2024, 1, 1): 100.0,
            date(2024, 2, 1): 110.0,
        })

        svc = DCABacktestService(price_repo, stock_repo)
        result = svc.run(
            tickers=["akbnk"],
            monthly_contribution=Decimal("1000"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 1),
        )

        # 2 aylık veri var (Ocak+Şubat) -> monthly_contribution_dates 2 katkı üretir.
        assert result.contribution_count == 2
        assert result.total_invested == Decimal("2000")
        assert result.final_value == Decimal("2100.000000000000000000000000")
        stock_repo.get_stock_by_ticker.assert_called_once_with("AKBNK")

    def test_unknown_ticker_is_skipped_without_crash(self):
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = None
        price_repo = MagicMock()

        svc = DCABacktestService(price_repo, stock_repo)
        result = svc.run(
            tickers=["YOK"],
            monthly_contribution=Decimal("1000"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 2, 1),
        )

        assert result.contribution_count == 0
        assert result.total_invested == Decimal("0")
        price_repo.get_price_series.assert_not_called()

    def test_custom_weights_are_respected(self):
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.side_effect = lambda t: {
            "A": _stock(1, "A"), "B": _stock(2, "B"),
        }[t]
        price_repo = MagicMock()
        price_repo.get_price_series.side_effect = lambda stock_id, start, end: (
            _rows(1, {date(2024, 1, 1): 100.0}) if stock_id == 1
            else _rows(2, {date(2024, 1, 1): 50.0})
        )

        svc = DCABacktestService(price_repo, stock_repo)
        result = svc.run(
            tickers=["A", "B"],
            monthly_contribution=Decimal("1000"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            weights={"A": 0.6, "B": 0.4},
        )

        assert result.shares_by_ticker["A"] == Decimal("6")
        assert result.shares_by_ticker["B"] == Decimal("8")
