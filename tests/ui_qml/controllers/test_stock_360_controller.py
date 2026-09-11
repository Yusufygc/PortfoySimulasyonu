"""Stock360Controller — Stock360View'un d2 veri köprüsü testleri."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import List
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.stock_360_service import StockOverview, TechnicalLevels
from src.domain.models.daily_price import DailyPrice
from src.domain.models.shareholder import ShareholderRow, ShareholderSnapshot
from src.domain.models.stock import Stock
from src.ui_qml.controllers.stock_360_controller import Stock360Controller


def _rows(stock_id: int, n: int, start: date) -> List[DailyPrice]:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.1
        rows.append(DailyPrice(
            id=None, stock_id=stock_id, price_date=start + timedelta(days=i),
            close_price=Decimal(str(round(close, 2))),
            open_price=Decimal(str(round(close - 1, 2))),
            high_price=Decimal(str(round(close + 2, 2))),
            low_price=Decimal(str(round(close - 2, 2))),
            volume=1000 + i,
        ))
    return rows


def _overview(**overrides) -> StockOverview:
    defaults = dict(
        ticker="AKBNK", last_price=Decimal("120"), last_price_date=date.today(),
        daily_change_pct=1.5, volume=1000, week52_low=Decimal("90"), week52_high=Decimal("150"),
    )
    defaults.update(overrides)
    return StockOverview(**defaults)


def _technical(**overrides) -> TechnicalLevels:
    defaults = dict(
        ticker="AKBNK", rsi14=55.0, macd_line=0.5, macd_signal=0.3,
        sma50=110.0, sma200=100.0, ema20=115.0, support=105.0, resistance=125.0,
    )
    defaults.update(overrides)
    return TechnicalLevels(**defaults)


def _financial_metrics() -> dict:
    return {
        "periods": ["2026/6", "2026/3"],
        "_market_val": {"fk": 5.2, "pddd": 1.1, "ev_favok": 3.9, "market_cap": 1000.0},
        "roe": {"2026/6": 32.0, "2026/3": 30.0},
    }


def _shareholder_snapshot(as_of: date) -> ShareholderSnapshot:
    return ShareholderSnapshot(
        creation_date=as_of,
        rows=(
            ShareholderRow("Kurucu Aile", Decimal("4000"), Decimal("40"), Decimal("40")),
            ShareholderRow("Yabancı Ortak", Decimal("1500"), Decimal("15"), Decimal("15")),
            ShareholderRow("TOPLAM", Decimal("5500"), Decimal("55"), Decimal("55"), is_total=True),
        ),
    )


_UNSET = object()


def _make_container(
    overview=_UNSET, technical=_UNSET, financial_metrics=None, financial_error=None,
    shareholder_snapshots=None, shareholder_error=None, row_count=400,
):
    container = MagicMock()
    container.stock_repo.get_stock_by_ticker.return_value = Stock(id=1, ticker="AKBNK", name="AKBNK", currency_code="TRY")
    container.price_repo.get_price_series.return_value = _rows(1, row_count, date.today() - timedelta(days=row_count))

    container.stock_360_service.get_overview.return_value = _overview() if overview is _UNSET else overview
    container.stock_360_service.get_technical_levels.return_value = _technical() if technical is _UNSET else technical

    if financial_error is not None:
        container.stock_360_service.get_financials.side_effect = financial_error
    else:
        container.stock_360_service.get_financials.return_value = (
            financial_metrics if financial_metrics is not None else _financial_metrics()
        )

    if shareholder_error is not None:
        container.stock_360_service.get_shareholders.side_effect = shareholder_error
    else:
        container.stock_360_service.get_shareholders.return_value = (
            shareholder_snapshots if shareholder_snapshots is not None else [_shareholder_snapshot(date.today())]
        )
    return container


class TestLoadTicker:
    def test_load_ticker_sets_ticker_and_populates_overview(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("akbnk")

        assert controller.ticker == "AKBNK"
        assert controller.notFound is False
        assert controller.lastPrice == 120.0
        assert controller.dailyChangePct == 1.5
        assert controller.volume == 1000
        assert controller.week52Low == 90.0
        assert controller.week52High == 150.0

    def test_not_found_ticker_sets_not_found_true(self, qapp):
        controller = Stock360Controller(_make_container(overview=None))
        controller.loadTicker("YOK")

        assert controller.notFound is True

    def test_technical_levels_populated(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")

        assert controller.rsi14 == 55.0
        assert controller.macdLine == 0.5
        assert controller.macdSignal == 0.3
        assert controller.sma50 == 110.0
        assert controller.sma200 == 100.0
        assert controller.ema20 == 115.0
        assert controller.support == 105.0
        assert controller.resistance == 125.0

    def test_empty_ticker_is_ignored(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("   ")
        assert controller.ticker == ""


class TestRangeKey:
    def test_default_range_key_is_3a(self, qapp):
        controller = Stock360Controller(_make_container())
        assert controller.rangeKey == "3A"

    def test_range_keys_lists_all_six_presets(self, qapp):
        controller = Stock360Controller(_make_container())
        assert set(controller.rangeKeys) == {"1G", "1H", "1A", "3A", "1Y", "5Y"}

    def test_invalid_range_key_is_ignored(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")
        controller.setRangeKey("GECERSIZ")
        assert controller.rangeKey == "3A"

    def test_smaller_range_yields_fewer_candlestick_bars(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")
        bars_3a = len(controller.candlestickBars)

        controller.setRangeKey("1A")
        bars_1a = len(controller.candlestickBars)

        assert bars_1a < bars_3a


class TestPriceSeries:
    def test_candlestick_bars_have_ohlc_keys(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")

        assert len(controller.candlestickBars) > 0
        bar = controller.candlestickBars[0]
        assert set(bar.keys()) == {"open", "high", "low", "close"}

    def test_candlestick_bars_skip_rows_without_ohlc(self, qapp):
        container = _make_container()
        rows = _rows(1, 400, date.today() - timedelta(days=400))
        rows[-1] = DailyPrice(
            id=None, stock_id=1, price_date=rows[-1].price_date,
            close_price=rows[-1].close_price,  # open/high/low yok
        )
        container.price_repo.get_price_series.return_value = rows

        controller = Stock360Controller(container)
        controller.loadTicker("AKBNK")

        # Eksik OHLC'li son satır mum listesine dahil edilmemeli.
        closes_in_bars = {b["close"] for b in controller.candlestickBars}
        assert float(rows[-1].close_price) not in closes_in_bars

    def test_rsi_and_macd_series_are_non_empty_with_enough_history(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")

        assert len(controller.rsiSeries) > 0
        assert len(controller.macdLineSeries) > 0
        assert len(controller.macdSignalSeries) > 0
        assert len(controller.rsiSeries) == len(controller.candlestickBars)

    def test_stale_ticker_still_shows_full_range_of_bars(self, qapp):
        # Son satırın tarihi "bugün"den çok geride (bkz. plan §9.12 veri güncelliği
        # bulgusu) — pencere son satıra göre değil literal "bugün"e göre kesilirse
        # neredeyse tüm barlar dışarıda kalır (regresyon testi).
        container = _make_container()
        stale_end = date.today() - timedelta(days=90)
        container.price_repo.get_price_series.return_value = _rows(1, 400, stale_end - timedelta(days=400))

        controller = Stock360Controller(container)
        controller.loadTicker("AKBNK")

        assert len(controller.candlestickBars) > 30  # 3A varsayılan aralık, tek bar değil

    def test_unknown_ticker_gives_empty_series(self, qapp):
        container = _make_container()
        container.stock_repo.get_stock_by_ticker.return_value = None
        controller = Stock360Controller(container)
        controller.loadTicker("YOK")

        assert controller.candlestickBars == []
        assert controller.rsiSeries == []


class TestFinancials:
    def test_ratios_populated_from_latest_period(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")

        assert controller.fk == 5.2
        assert controller.pddd == 1.1
        assert controller.evFavok == 3.9
        assert controller.roe == 32.0
        assert controller.financialPeriod == "2026/6"
        assert controller.financialsError == ""

    def test_financial_service_error_is_isolated(self, qapp):
        controller = Stock360Controller(_make_container(financial_error=RuntimeError("İş Yatırım erişilemedi")))
        controller.loadTicker("AKBNK")

        assert "erişilemedi" in controller.financialsError
        # Diğer boyutlar etkilenmemeli:
        assert controller.lastPrice == 120.0
        assert len(controller.candlestickBars) > 0


class TestShareholders:
    def test_shareholder_rows_and_free_float_computed(self, qapp):
        controller = Stock360Controller(_make_container())
        controller.loadTicker("AKBNK")

        assert controller.shareholderNames == ["Kurucu Aile", "Yabancı Ortak"]
        assert controller.shareholderRatios == [40.0, 15.0]
        assert controller.freeFloatPct == pytest.approx(45.0)  # 100 - (40+15)
        assert controller.shareholderSnapshotCount == 1
        assert controller.shareholdersError == ""

    def test_no_snapshots_gives_empty_and_zero_free_float(self, qapp):
        controller = Stock360Controller(_make_container(shareholder_snapshots=[]))
        controller.loadTicker("AKBNK")

        assert controller.shareholderNames == []
        assert controller.freeFloatPct == 0.0

    def test_shareholder_service_error_is_isolated(self, qapp):
        controller = Stock360Controller(_make_container(shareholder_error=RuntimeError("KAP erişilemedi")))
        controller.loadTicker("AKBNK")

        assert "erişilemedi" in controller.shareholdersError
        assert controller.lastPrice == 120.0
