"""ScreenerController — ScreenerView'un d3 veri köprüsü testleri."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.analysis.stock_360_service import StockOverview, TechnicalLevels
from src.application.services.analysis.technical.screener import SCREENER_FILTERS
from src.application.services.analysis.technical.screener_service import ScreenerMatch
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock
from src.ui_qml.controllers.screener_controller import ScreenerController


def _match(ticker: str, filter_key: str, close: float) -> ScreenerMatch:
    label = SCREENER_FILTERS[filter_key].label
    return ScreenerMatch(ticker=ticker, filter_key=filter_key, filter_label=label, close_price=close)


def _make_container(matches=None, overview=None, technical=None, price_rows=None):
    container = MagicMock()
    container.screener_service.scan.return_value = matches if matches is not None else []
    container.stock_360_service.get_overview.return_value = overview
    container.stock_360_service.get_technical_levels.return_value = technical
    container.stock_repo.get_stock_by_ticker.return_value = Stock(id=1, ticker="AKBNK", name="AKBNK", currency_code="TRY")
    container.price_repo.get_price_series.return_value = price_rows or []
    return container


class TestFilters:
    def test_filter_keys_and_labels_match_registry(self, qapp):
        controller = ScreenerController(_make_container())
        assert controller.filterKeys == list(SCREENER_FILTERS.keys())
        assert controller.filterLabels == [d.label for d in SCREENER_FILTERS.values()]

    def test_all_filters_active_by_default(self, qapp):
        controller = ScreenerController(_make_container())
        assert set(controller.activeFilters) == set(SCREENER_FILTERS.keys())

    def test_toggle_filter_removes_and_readds(self, qapp):
        container = _make_container()
        controller = ScreenerController(container)
        key = next(iter(SCREENER_FILTERS.keys()))

        controller.toggleFilter(key)
        assert key not in controller.activeFilters

        controller.toggleFilter(key)
        assert key in controller.activeFilters

    def test_unknown_filter_key_is_ignored(self, qapp):
        controller = ScreenerController(_make_container())
        before = set(controller.activeFilters)
        controller.toggleFilter("GECERSIZ")
        assert set(controller.activeFilters) == before

    def test_toggle_filter_triggers_rescan_with_updated_keys(self, qapp):
        container = _make_container()
        controller = ScreenerController(container)
        key = next(iter(SCREENER_FILTERS.keys()))

        controller.toggleFilter(key)

        last_call_keys = container.screener_service.scan.call_args.kwargs["filter_keys"]
        assert key not in last_call_keys


class TestResults:
    def test_run_scan_populates_parallel_result_lists(self, qapp):
        matches = [
            _match("AKBNK", "rsi_oversold_above_ema200", 45.0),
            _match("THYAO", "bollinger_lower_band_touch", 250.0),
        ]
        controller = ScreenerController(_make_container(matches=matches))

        assert controller.resultTickers == ["AKBNK", "THYAO"]
        assert controller.resultClosePrices == [45.0, 250.0]
        assert len(controller.resultFilterLabels) == 2
        assert controller.resultTrends == ["Boğa", "Boğa"]  # şu an sadece bullish filtre var

    def test_empty_scan_gives_empty_results(self, qapp):
        controller = ScreenerController(_make_container(matches=[]))
        assert controller.resultTickers == []


class TestSelectTicker:
    def test_select_ticker_populates_mini_overview(self, qapp):
        overview = StockOverview(
            ticker="AKBNK", last_price=Decimal("120"), last_price_date=date.today(),
            daily_change_pct=1.5, volume=1000, week52_low=Decimal("90"), week52_high=Decimal("150"),
        )
        technical = TechnicalLevels(
            ticker="AKBNK", rsi14=28.0, macd_line=0.4, macd_signal=0.1,
            sma50=110.0, sma200=100.0, ema20=115.0, support=105.0, resistance=125.0,
        )
        controller = ScreenerController(_make_container(overview=overview, technical=technical))

        controller.selectTicker("akbnk")

        assert controller.selectedTicker == "AKBNK"
        assert controller.miniLastPrice == 120.0
        assert controller.miniRsi14 == 28.0
        assert controller.miniMacdLine == 0.4
        assert controller.miniMacdSignal == 0.1

    def test_select_ticker_populates_sparkline_from_price_series(self, qapp):
        rows = [
            DailyPrice(id=None, stock_id=1, price_date=date.today() - timedelta(days=2), close_price=Decimal("10")),
            DailyPrice(id=None, stock_id=1, price_date=date.today() - timedelta(days=1), close_price=Decimal("11")),
            DailyPrice(id=None, stock_id=1, price_date=date.today(), close_price=Decimal("12")),
        ]
        controller = ScreenerController(_make_container(price_rows=rows))

        controller.selectTicker("AKBNK")

        assert controller.sparklineValues == [10.0, 11.0, 12.0]

    def test_stale_ticker_still_shows_full_sparkline_window(self, qapp):
        # Son satırın tarihi "bugün"den ~90 gün geride (bkz. §9.12 veri güncelliği
        # bulgusu) — pencere literal "bugün"e göre kesilirse tek satır kalır.
        stale_end = date.today() - timedelta(days=90)
        rows = [
            DailyPrice(id=None, stock_id=1, price_date=stale_end - timedelta(days=i), close_price=Decimal(str(10 + i)))
            for i in range(60)
        ]
        controller = ScreenerController(_make_container(price_rows=rows))

        controller.selectTicker("AKBNK")

        assert len(controller.sparklineValues) > 1

    def test_select_unknown_ticker_gives_empty_sparkline(self, qapp):
        container = _make_container()
        container.stock_repo.get_stock_by_ticker.return_value = None
        controller = ScreenerController(container)

        controller.selectTicker("YOK")

        assert controller.sparklineValues == []

    def test_empty_ticker_is_ignored(self, qapp):
        controller = ScreenerController(_make_container())
        controller.selectTicker("   ")
        assert controller.selectedTicker == ""
