"""Genel Bakış kayan şeridi: portföyden bağımsız rastgele BIST hisseleri."""
from __future__ import annotations

from types import SimpleNamespace

from src.domain.constants.bist_tickers import BIST_TICKERS
from src.ui_qml.controllers.chart_controller import ChartController


class _Lookup:
    def __init__(self, tickers):
        self._tickers = tickers

    def list_market_tickers(self):
        return self._tickers

    def get_market_bars(self, *args, **kwargs):
        return []


def test_samples_from_market_universe_without_duplicates():
    universe = [f"T{i:03d}" for i in range(100)]
    controller = ChartController(container=SimpleNamespace(stock_lookup_service=_Lookup(universe)))
    picked = controller.marketTickers
    assert len(picked) == 24 and len(set(picked)) == 24 and set(picked) <= set(universe)


def test_falls_back_to_bist_list_without_container_or_universe():
    assert set(ChartController(container=None).marketTickers) <= BIST_TICKERS
    assert set(ChartController(container=SimpleNamespace(stock_lookup_service=_Lookup([]))).marketTickers) <= BIST_TICKERS


def test_small_universe_is_not_oversampled():
    controller = ChartController(container=SimpleNamespace(stock_lookup_service=_Lookup(["AAA", "BBB", "CCC"])))
    assert sorted(controller.marketTickers) == ["AAA", "BBB", "CCC"]


def test_does_not_depend_on_portfolio_and_shuffle_emits():
    controller = ChartController(container=SimpleNamespace(stock_lookup_service=_Lookup([f"T{i:03d}" for i in range(200)])))
    seen = []
    controller.marketTickersChanged.connect(lambda: seen.append(1))
    before = list(controller.marketTickers)
    controller.shuffleMarketTickers()
    assert seen == [1] and controller.marketTickers != before
