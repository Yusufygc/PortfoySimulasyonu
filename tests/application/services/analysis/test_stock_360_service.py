"""Stock360Service — birleşik Hisse 360 servisi orkestrasyon testleri (mock repo/servis)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.stock_360_service import Stock360Service
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock


def _stock(id_: int = 1, ticker: str = "AKBNK") -> Stock:
    return Stock(id=id_, ticker=ticker, name=ticker, currency_code="TRY")


def _rows(stock_id: int, closes: list[float], start: date = date(2024, 1, 1)) -> list[DailyPrice]:
    return [
        DailyPrice(
            id=None,
            stock_id=stock_id,
            price_date=start + timedelta(days=i),
            close_price=Decimal(str(c)),
            high_price=Decimal(str(c + 1)),
            low_price=Decimal(str(c - 1)),
            volume=1000 + i,
        )
        for i, c in enumerate(closes)
    ]


def _make_service(price_repo=None, stock_repo=None, financial_service=None, shareholder_service=None):
    stock_repo = stock_repo or MagicMock()
    stock_repo.get_stock_by_ticker.return_value = _stock()
    return Stock360Service(
        price_repo=price_repo or MagicMock(),
        stock_repo=stock_repo,
        financial_analysis_service=financial_service or MagicMock(),
        shareholder_analysis_service=shareholder_service or MagicMock(),
    )


class TestGetOverview:
    def test_unknown_ticker_returns_none(self):
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = None
        svc = _make_service(stock_repo=stock_repo)

        assert svc.get_overview("YOK") is None

    def test_computes_change_pct_and_52w_range(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, [100.0, 90.0, 110.0])
        svc = _make_service(price_repo=price_repo)

        overview = svc.get_overview("AKBNK")

        assert overview.last_price == Decimal("110.0")
        assert overview.daily_change_pct == pytest.approx(22.222222, rel=1e-4)  # (110-90)/90
        assert overview.week52_low == Decimal("90.0")
        assert overview.week52_high == Decimal("110.0")
        assert overview.volume == 1002

    def test_single_row_has_no_change_pct(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, [100.0])
        svc = _make_service(price_repo=price_repo)

        overview = svc.get_overview("AKBNK")

        assert overview.daily_change_pct is None
        assert overview.week52_low == overview.week52_high == Decimal("100.0")

    def test_no_price_rows_returns_none(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = []
        svc = _make_service(price_repo=price_repo)

        assert svc.get_overview("AKBNK") is None


class TestGetTechnicalLevels:
    def test_insufficient_data_returns_none(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, [100.0] * 10)
        svc = _make_service(price_repo=price_repo)

        assert svc.get_technical_levels("AKBNK") is None

    def test_sufficient_data_computes_rsi_and_macd(self):
        closes = [100.0 + (i % 5) - (i % 3) for i in range(60)]
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, closes)
        svc = _make_service(price_repo=price_repo)

        levels = svc.get_technical_levels("AKBNK")

        assert levels is not None
        assert levels.rsi14 is not None
        assert levels.macd_line is not None
        assert levels.sma50 is not None
        assert levels.sma200 is None  # 60 satır < 200, ısınmıyor
        assert levels.ema20 is not None


class TestDelegatingCalls:
    def test_get_financials_delegates_to_financial_service(self):
        financial_service = MagicMock()
        financial_service.analyze.return_value = {"periods": ["2024/12"]}
        svc = _make_service(financial_service=financial_service)

        result = svc.get_financials("akbnk", n_quarters=8, currency="USD")

        assert result == {"periods": ["2024/12"]}
        financial_service.analyze.assert_called_once_with("akbnk", n_quarters=8, currency="USD")

    def test_get_shareholders_delegates_to_shareholder_service(self):
        shareholder_service = MagicMock()
        shareholder_service.get_history.return_value = ["snap"]
        svc = _make_service(shareholder_service=shareholder_service)

        result = svc.get_shareholders("akbnk", force_refresh=True)

        assert result == ["snap"]
        shareholder_service.get_history.assert_called_once_with("akbnk", force_refresh=True)


class TestGetSnapshot:
    def test_combines_all_dimensions(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, [100.0, 110.0])
        financial_service = MagicMock()
        financial_service.analyze.return_value = {"periods": ["2024/12"]}
        shareholder_service = MagicMock()
        shareholder_service.get_history.return_value = ["snap"]
        svc = _make_service(
            price_repo=price_repo,
            financial_service=financial_service,
            shareholder_service=shareholder_service,
        )

        snap = svc.get_snapshot("akbnk")

        assert snap.ticker == "AKBNK"
        assert snap.overview is not None
        assert snap.financials == {"periods": ["2024/12"]}
        assert snap.financials_error is None
        assert snap.shareholders == ["snap"]
        assert snap.shareholders_error is None

    def test_financial_service_error_is_isolated(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, [100.0, 110.0])
        financial_service = MagicMock()
        financial_service.analyze.side_effect = RuntimeError("İş Yatırım erişilemedi")
        shareholder_service = MagicMock()
        shareholder_service.get_history.return_value = ["snap"]
        svc = _make_service(
            price_repo=price_repo,
            financial_service=financial_service,
            shareholder_service=shareholder_service,
        )

        snap = svc.get_snapshot("akbnk")

        assert snap.financials is None
        assert "erişilemedi" in snap.financials_error
        # Diğer boyutlar hâlâ dolu:
        assert snap.overview is not None
        assert snap.shareholders == ["snap"]

    def test_shareholder_service_error_is_isolated(self):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _rows(1, [100.0, 110.0])
        shareholder_service = MagicMock()
        shareholder_service.get_history.side_effect = RuntimeError("KAP erişilemedi")
        svc = _make_service(price_repo=price_repo, shareholder_service=shareholder_service)

        snap = svc.get_snapshot("akbnk")

        assert snap.shareholders == []
        assert "erişilemedi" in snap.shareholders_error
        assert snap.overview is not None
