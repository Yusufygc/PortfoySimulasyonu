"""StrategyBacktestService — doğrulama, veri okuma ve Markowitz ağırlıklı yeniden dengeleme (gerçek hesap, sahte depo)."""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from src.application.services.planning.optimization_service import compute_max_sharpe_weights
from src.application.services.simulation.strategy_backtest_service import (
    WEIGHTING_EQUAL,
    WEIGHTING_MARKOWITZ,
    StrategyBacktestService,
)

CAPITAL = Decimal("100000")
START, END = date(2025, 1, 2), date(2025, 12, 31)


def _business_days(start: date, end: date):
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _walk(seed: int, drift: float, vol: float, days: list[date]) -> dict[date, float]:
    rng = np.random.default_rng(seed)
    returns = rng.normal(drift, vol, len(days))
    prices = 100 * np.exp(np.cumsum(returns))
    return dict(zip(days, prices))


class FakeMarketHistory:
    def __init__(self, series_by_ticker):
        self._series = series_by_ticker

    def get_price_series(self, ticker, start, end):
        return [
            SimpleNamespace(price_date=d, close_price=Decimal(str(round(p, 4))))
            for d, p in sorted(self._series.get(ticker, {}).items())
            if start <= d <= end
        ]


def _service(series_by_ticker):
    no_stocks = SimpleNamespace(get_stock_by_ticker=lambda _ticker: None)
    return StrategyBacktestService(price_repo=None, stock_repo=no_stocks, market_history_repo=FakeMarketHistory(series_by_ticker))


@pytest.fixture(scope="module")
def three_stocks():
    days = list(_business_days(date(2023, 11, 1), END))
    return {
        "AAA": _walk(1, 0.0010, 0.012, days),
        "BBB": _walk(2, 0.0002, 0.020, days),
        "CCC": _walk(3, 0.0005, 0.015, days),
    }


class TestComputeMaxSharpeWeights:
    def _prices(self, three_stocks):
        return pd.DataFrame(three_stocks).tail(300)

    def test_weights_sum_to_one_and_respect_cap(self, three_stocks):
        weights = compute_max_sharpe_weights(self._prices(three_stocks))

        assert set(weights) == {"AAA", "BBB", "CCC"}
        assert sum(weights.values()) == pytest.approx(1.0)
        assert all(0.0 <= w <= 0.40 + 1e-6 for w in weights.values())

    def test_rejects_single_asset(self, three_stocks):
        with pytest.raises(ValueError):
            compute_max_sharpe_weights(self._prices(three_stocks)[["AAA"]])

    def test_rejects_short_history(self, three_stocks):
        with pytest.raises(ValueError):
            compute_max_sharpe_weights(self._prices(three_stocks).tail(30))


class TestRebalancingService:
    def test_equal_weight_run_returns_series_and_baseline(self, three_stocks):
        result = _service(three_stocks).run_rebalancing(
            ["aaa", "BBB.IS", "ccc"], CAPITAL, START, END, rebalance_every_months=3, weighting=WEIGHTING_EQUAL
        )

        assert result.start_date >= START and result.end_date <= END
        assert result.rebalance_count == 3  # Nis, Tem, Eki
        assert len(result.strategy_series) == len(result.baseline_series) > 200
        assert result.strategy_series[result.start_date] == result.baseline_series[result.start_date] == CAPITAL
        assert result.total_return_pct is not None and result.baseline_return_pct is not None

    def test_markowitz_uses_warmup_history_and_changes_weights(self, three_stocks):
        result = _service(three_stocks).run_rebalancing(
            ["AAA", "BBB", "CCC"], CAPITAL, START, END, rebalance_every_months=3, weighting=WEIGHTING_MARKOWITZ
        )

        assert result.start_date == START or result.start_date <= date(2025, 1, 6)
        assert not [e for e in result.events if e.action == "FALLBACK"]
        assert any(e.action == "REBALANCE" for e in result.events)
        # Maksimum Sharpe ağırlıkları eşit ağırlıktan farklıdır, bu yüzden strateji tabanı tutmaz
        equal = _service(three_stocks).run_rebalancing(["AAA", "BBB", "CCC"], CAPITAL, START, END, 3, WEIGHTING_EQUAL)
        assert result.final_value != equal.final_value

    def test_markowitz_without_warmup_data_falls_back_to_equal_and_reports(self):
        days = list(_business_days(START, END))
        data = {"AAA": _walk(1, 0.001, 0.01, days), "BBB": _walk(2, 0.0, 0.02, days)}
        # Başlangıçtan önce veri yok: ilk gün 60 gün geçmiş yok -> eşit ağırlık
        result = _service(data).run_rebalancing(["AAA", "BBB"], CAPITAL, START, END, 6, WEIGHTING_MARKOWITZ)

        fallback = [e for e in result.events if e.action == "FALLBACK"]
        assert fallback and fallback[0].event_date == result.start_date
        assert result.final_value > 0

    @pytest.mark.parametrize(
        "kwargs,message",
        [
            (dict(tickers=["AAA"]), "en az 2 hisse"),
            (dict(tickers=["AAA", "BBB"], weighting="kelly"), "Ağırlık yöntemi"),
            (dict(tickers=["AAA", "BBB"], rebalance_every_months=0), "1 ile 12"),
            (dict(tickers=["AAA", "BBB"], initial_capital=Decimal("0")), "sermaye"),
            (dict(tickers=["AAA", "BBB"], start_date=END, end_date=START), "Bitiş tarihi"),
            (dict(tickers=["AAA", "BBB"], commission_rate=0.5), "Komisyon"),
            (dict(tickers=["YOK1", "YOK2"]), "fiyat verisi bulunamadı"),
        ],
    )
    def test_validation_errors(self, three_stocks, kwargs, message):
        params = dict(tickers=["AAA", "BBB"], initial_capital=CAPITAL, start_date=START, end_date=END)
        params.update(kwargs)

        with pytest.raises(ValueError, match=message):
            _service(three_stocks).run_rebalancing(**params)


class TestStopTakeService:
    def test_runs_on_real_series_and_reports_exits(self, three_stocks):
        result = _service(three_stocks).run_stop_take(
            ["AAA", "BBB", "CCC"], CAPITAL, START, END, stop_loss_pct=8, take_profit_pct=15
        )

        assert result.exit_count == len([e for e in result.events if e.action in ("STOP_LOSS", "TAKE_PROFIT")])
        assert result.exit_count > 0
        assert result.strategy_series[result.start_date] == CAPITAL

    @pytest.mark.parametrize(
        "kwargs,message",
        [
            (dict(stop_loss_pct=None, take_profit_pct=None), "en az birini"),
            (dict(stop_loss_pct=0), "0'dan büyük"),
            (dict(stop_loss_pct=100), "%100"),
            (dict(stop_loss_pct=5, take_profit_pct=-1), "0'dan büyük"),
            (dict(stop_loss_pct=5, tickers=[]), "hisse kodu"),
        ],
    )
    def test_validation_errors(self, three_stocks, kwargs, message):
        params = dict(tickers=["AAA"], initial_capital=CAPITAL, start_date=START, end_date=END, stop_loss_pct=5)
        params.update(kwargs)

        with pytest.raises(ValueError, match=message):
            _service(three_stocks).run_stop_take(**params)
