"""ADX ve Supertrend — trend gücü/yönü indikatörleri, saf vektörel hesap testleri."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.application.services.analysis.technical.indicators import adx, supertrend


def _make_series(values: list[float], start: date = date(2020, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(values, index=idx)


def _ohlc_from_closes(closes: list[float], spread: float = 1.0):
    ser = _make_series(closes)
    return ser + spread, ser - spread, ser


class TestADX:
    def test_warmup_bars_are_nan(self):
        highs, lows, closes = _ohlc_from_closes([100.0 + i for i in range(60)])
        adx_line, plus_di, minus_di = adx(highs, lows, closes, period=14)
        assert adx_line.iloc[:14].isna().all()
        assert plus_di.iloc[:13].isna().all()
        assert minus_di.iloc[:13].isna().all()

    def test_strong_uptrend_has_high_adx_and_plus_di_dominates(self):
        highs, lows, closes = _ohlc_from_closes([100.0 + 2.0 * i for i in range(80)])
        adx_line, plus_di, minus_di = adx(highs, lows, closes, period=14)
        assert adx_line.iloc[-1] > 25.0
        assert plus_di.iloc[-1] > minus_di.iloc[-1]

    def test_strong_downtrend_has_high_adx_and_minus_di_dominates(self):
        highs, lows, closes = _ohlc_from_closes([300.0 - 2.0 * i for i in range(80)])
        adx_line, plus_di, minus_di = adx(highs, lows, closes, period=14)
        assert adx_line.iloc[-1] > 25.0
        assert minus_di.iloc[-1] > plus_di.iloc[-1]

    def test_sideways_market_has_low_adx(self):
        highs, lows, closes = _ohlc_from_closes([100.0 + (i % 2) * 0.5 for i in range(100)])
        adx_line, _, _ = adx(highs, lows, closes, period=14)
        assert adx_line.iloc[-1] < 20.0

    def test_values_stay_within_zero_and_hundred(self):
        closes = [100.0 + (i * 7) % 13 - (i % 5) * 3 for i in range(120)]
        highs, lows, closes_ser = _ohlc_from_closes(closes, spread=2.0)
        adx_line, plus_di, minus_di = adx(highs, lows, closes_ser, period=14)
        for series in (adx_line.dropna(), plus_di.dropna(), minus_di.dropna()):
            assert ((series >= 0.0) & (series <= 100.0)).all()

    def test_flat_prices_without_range_do_not_divide_by_zero(self):
        flat = _make_series([50.0] * 60)
        adx_line, _, _ = adx(flat, flat, flat, period=14)
        assert adx_line.dropna().eq(0.0).all()


class TestSupertrend:
    def test_warmup_direction_is_zero_and_line_nan(self):
        highs, lows, closes = _ohlc_from_closes([100.0 + i for i in range(40)])
        line, direction = supertrend(highs, lows, closes, period=10, multiplier=3.0)
        assert (direction.iloc[:9] == 0).all()
        assert line.iloc[:9].isna().all()
        assert direction.iloc[9] == 1

    def test_uptrend_line_stays_below_price_and_never_falls(self):
        highs, lows, closes = _ohlc_from_closes([100.0 + 2.0 * i for i in range(80)])
        line, direction = supertrend(highs, lows, closes, period=10, multiplier=3.0)
        valid = direction != 0
        assert (direction[valid] == 1).all()
        assert (line[valid] < closes[valid]).all()
        assert line[valid].is_monotonic_increasing

    def test_reversal_flips_direction_both_ways(self):
        up = [100.0 + 2.0 * i for i in range(60)]
        down = [up[-1] - 3.0 * i for i in range(1, 60)]
        recovery = [down[-1] + 4.0 * i for i in range(1, 60)]
        highs, lows, closes = _ohlc_from_closes(up + down + recovery)
        line, direction = supertrend(highs, lows, closes, period=10, multiplier=3.0)
        assert direction.iloc[55] == 1
        assert direction.iloc[100] == -1
        assert direction.iloc[-1] == 1
        assert line.iloc[100] > closes.iloc[100]  # düşüşte çizgi fiyatın üstünde
        assert line.iloc[-1] < closes.iloc[-1]    # yükselişte çizgi fiyatın altında

    def test_series_are_aligned_with_input_index(self):
        highs, lows, closes = _ohlc_from_closes([100.0 + i for i in range(30)])
        line, direction = supertrend(highs, lows, closes)
        assert line.index.equals(closes.index)
        assert direction.index.equals(closes.index)
