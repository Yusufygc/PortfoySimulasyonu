"""Strateji backtest motoru (yeniden dengeleme, stop-loss / take-profit) — saf hesap testleri."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.application.services.simulation.strategy_backtest import (
    equal_weight_function,
    max_drawdown_pct,
    rebalance_dates,
    simulate_rebalancing,
    simulate_stop_take,
)

CAPITAL = Decimal("1000")


def _series(rows):
    """rows: [(date, {ticker: price})] -> PriceSeries"""
    return {d: {t: Decimal(str(p)) for t, p in prices.items()} for d, prices in rows}


MONTHLY = [date(2026, m, 2) for m in range(1, 7)]  # Oca-Haz, her ayın 2'si


class TestRebalanceDates:
    def test_monthly_picks_first_trading_day_after_start(self):
        days = [date(2026, 1, 2), date(2026, 1, 5), date(2026, 2, 2), date(2026, 2, 3), date(2026, 3, 4)]

        assert rebalance_dates(days, date(2026, 1, 2), 1) == [date(2026, 2, 2), date(2026, 3, 4)]

    def test_quarterly_skips_intermediate_months(self):
        assert rebalance_dates(MONTHLY, MONTHLY[0], 3) == [date(2026, 4, 2)]

    def test_interval_must_be_positive(self):
        with pytest.raises(ValueError):
            rebalance_dates(MONTHLY, MONTHLY[0], 0)


class TestMaxDrawdown:
    def test_peak_to_trough(self):
        series = {date(2026, 1, 1): Decimal("100"), date(2026, 1, 2): Decimal("120"), date(2026, 1, 3): Decimal("90")}

        assert max_drawdown_pct(series) == pytest.approx(-25.0)

    def test_empty_is_none(self):
        assert max_drawdown_pct({}) is None


class TestRebalancing:
    def _run(self, rows, months=1, commission=0.0, weight_fn=None, tickers=("A", "B")):
        return simulate_rebalancing(
            _series(rows), list(tickers), CAPITAL, rows[0][0], months,
            weight_fn or equal_weight_function(list(tickers)), commission,
        )

    def test_constant_prices_change_nothing(self):
        result = self._run([(d, {"A": 100, "B": 100}) for d in MONTHLY])

        assert set(result.strategy_series.values()) == {CAPITAL}
        assert result.final_value == result.baseline_final_value == CAPITAL
        assert result.total_return_pct == pytest.approx(0.0)

    def test_rebalancing_locks_in_gains_and_beats_buy_and_hold_on_mean_reversion(self):
        # A ikiye katlanıp geri döner, B sabit. Şubat'ta dengeleyen strateji A'nın bir kısmını yüksekten satmıştır.
        rows = [
            (date(2026, 1, 2), {"A": 100, "B": 100}),
            (date(2026, 2, 2), {"A": 200, "B": 100}),
            (date(2026, 3, 2), {"A": 100, "B": 100}),
        ]

        result = self._run(rows)

        assert result.baseline_series[date(2026, 2, 2)] == Decimal("1500")
        assert result.strategy_series[date(2026, 2, 2)] == Decimal("1500")  # dengeleme değeri değiştirmez
        assert result.baseline_final_value == Decimal("1000")
        assert result.final_value == Decimal("1125")  # 750/200*100 + 750
        assert result.rebalance_count == 2
        assert [e.ticker for e in result.events if e.action == "REBALANCE"][:2] == ["A", "B"]

    def test_quarterly_interval_rebalances_less_often(self):
        rows = [(d, {"A": 100 + i * 10, "B": 100}) for i, d in enumerate(MONTHLY)]

        monthly = self._run(rows, months=1)
        quarterly = self._run(rows, months=3)

        assert monthly.rebalance_count == 5
        assert quarterly.rebalance_count == 1

    def test_commission_reduces_initial_value_and_each_rebalance(self):
        rows = [(date(2026, 1, 2), {"A": 100, "B": 100}), (date(2026, 2, 2), {"A": 200, "B": 100})]

        result = self._run(rows, commission=0.01)

        assert result.strategy_series[date(2026, 1, 2)] == Decimal("990")
        assert result.baseline_series[date(2026, 2, 2)] == Decimal("1485")
        assert result.final_value < result.baseline_final_value  # dengeleme masrafı aynı fiyat yolunda kayıp

    def test_custom_weights_are_normalized_and_applied(self):
        rows = [(date(2026, 1, 2), {"A": 100, "B": 100}), (date(2026, 2, 2), {"A": 200, "B": 100})]

        result = self._run(rows, weight_fn=lambda _d, _h: {"A": 3.0, "B": 1.0})

        assert result.baseline_series[date(2026, 2, 2)] == Decimal("1750")  # 750*2 + 250

    def test_failing_weight_function_falls_back_to_equal_and_records_event(self):
        def broken(_d, _h):
            raise ValueError("veri yok")

        rows = [(date(2026, 1, 2), {"A": 100, "B": 100}), (date(2026, 2, 2), {"A": 200, "B": 100})]

        result = self._run(rows, weight_fn=broken)

        assert [e.action for e in result.events].count("FALLBACK") == 2
        assert result.baseline_series[date(2026, 2, 2)] == Decimal("1500")

    def test_start_moves_to_first_day_all_tickers_have_prices(self):
        rows = [
            (date(2026, 1, 2), {"A": 100}),
            (date(2026, 2, 2), {"A": 100, "B": 50}),
            (date(2026, 3, 2), {"A": 100, "B": 50}),
        ]

        result = self._run(rows)

        assert result.start_date == date(2026, 2, 2)

    def test_ticker_without_any_price_is_reported_and_skipped(self):
        rows = [(date(2026, 1, 2), {"A": 100}), (date(2026, 2, 2), {"A": 110})]

        result = self._run(rows, tickers=("A", "YOK"))

        assert result.skipped_tickers == ["YOK"]
        assert result.final_value == Decimal("1100")

    def test_history_before_start_is_passed_to_weight_function_without_lookahead(self):
        seen = {}

        def spy(as_of, history):
            seen[as_of] = (len(history), history.index.max())
            return {"A": 1.0, "B": 1.0}

        rows = [(date(2025, 12, 1), {"A": 90, "B": 90})] + [(d, {"A": 100, "B": 100}) for d in MONTHLY[:3]]
        simulate_rebalancing(_series(rows), ["A", "B"], CAPITAL, date(2026, 1, 2), 1, spy)

        assert seen[date(2026, 1, 2)] == (2, date(2026, 1, 2))  # ısınma barı + başlangıç, sonrası yok
        assert seen[date(2026, 2, 2)][1] == date(2026, 2, 2)

    def test_no_data_returns_empty_result(self):
        result = simulate_rebalancing({}, ["A", "B"], CAPITAL, date(2026, 1, 1), 1, equal_weight_function(["A", "B"]))

        assert result.strategy_series == {} and result.total_return_pct is None


class TestStopTake:
    def _run(self, a_prices, stop=None, take=None, extra=None, commission=0.0):
        days = [date(2026, 1, 1) + timedelta(days=i) for i in range(len(a_prices))]
        rows = [(d, {"A": p, **({"B": extra[i]} if extra else {})}) for i, (d, p) in enumerate(zip(days, a_prices))]
        tickers = ["A", "B"] if extra else ["A"]
        return simulate_stop_take(_series(rows), tickers, CAPITAL, days[0], stop, take, commission), days

    def test_stop_loss_sells_at_threshold_and_stays_in_cash(self):
        result, days = self._run([100, 95, 90, 70, 50], stop=10)

        assert result.exit_count == 1
        event = result.events[0]
        assert (event.action, event.ticker, event.event_date) == ("STOP_LOSS", "A", days[2])
        assert result.strategy_series[days[2]] == Decimal("900")
        assert result.final_value == Decimal("900")          # nakitte kaldı, sonraki düşüş etkilemedi
        assert result.baseline_final_value == Decimal("500")  # al ve tut düşüşü yaşadı

    def test_take_profit_locks_gain_and_misses_further_upside(self):
        result, days = self._run([100, 110, 120, 150], take=20)

        assert [e.action for e in result.events] == ["TAKE_PROFIT"]
        assert result.final_value == Decimal("1200")
        assert result.baseline_final_value == Decimal("1500")

    def test_no_trigger_matches_buy_and_hold(self):
        result, _ = self._run([100, 101, 102], stop=20, take=50)

        assert result.exit_count == 0
        assert result.final_value == result.baseline_final_value == Decimal("1020")

    def test_each_position_is_checked_independently(self):
        result, days = self._run([100, 100, 100], stop=10, extra=[100, 85, 85])

        assert [(e.ticker, e.action) for e in result.events] == [("B", "STOP_LOSS")]
        assert result.final_value == Decimal("500") * Decimal("1") + Decimal("425")  # A tutuluyor, B 85'ten satıldı

    def test_commission_is_charged_on_entry_and_exit(self):
        result, days = self._run([100, 80], stop=10, commission=0.01)

        # 990 yatırım -> 9,9 lot; 80'den satış 792 - %1 = 784,08
        assert result.strategy_series[days[0]] == Decimal("990")
        assert result.final_value == Decimal("784.08")

    def test_requires_at_least_one_threshold(self):
        with pytest.raises(ValueError):
            simulate_stop_take(_series([(date(2026, 1, 1), {"A": 100})]), ["A"], CAPITAL, date(2026, 1, 1), None, None)

    def test_drawdown_is_lower_for_stopped_strategy(self):
        result, _ = self._run([100, 90, 60, 40], stop=10)

        assert result.max_drawdown_pct > result.baseline_max_drawdown_pct
