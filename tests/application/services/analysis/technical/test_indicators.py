"""Temel teknik indikatörler (SMA/EMA/RSI/MACD) — saf vektörel hesap testleri."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from src.application.services.analysis.technical.indicators import (
    atr,
    bollinger_bands,
    cci,
    ema,
    macd,
    obv,
    rsi,
    sma,
    stochastic_oscillator,
    vwap,
)


def _make_series(values: list[float], start: date = date(2020, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(values, index=idx)


class TestSMA:
    def test_empty_series_returns_empty(self):
        assert sma(pd.Series([], dtype=float), period=3).empty

    def test_warmup_bars_are_nan(self):
        ser = _make_series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = sma(ser, period=3)
        assert result.iloc[0:2].isna().all()

    def test_known_values(self):
        ser = _make_series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = sma(ser, period=3)
        assert result.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
        assert result.iloc[3] == pytest.approx(3.0)  # (2+3+4)/3
        assert result.iloc[4] == pytest.approx(4.0)  # (3+4+5)/3


class TestEMA:
    def test_empty_series_returns_empty(self):
        assert ema(pd.Series([], dtype=float), period=3).empty

    def test_warmup_bars_are_nan(self):
        ser = _make_series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ema(ser, period=3)
        assert result.iloc[0:2].isna().all()

    def test_known_values_alpha_recursion(self):
        # period=3 -> alpha=2/(3+1)=0.5, seed=x[0].
        # ema[0]=1, ema[1]=0.5*2+0.5*1=1.5, ema[2]=0.5*3+0.5*1.5=2.25, ema[3]=0.5*4+0.5*2.25=3.125
        ser = _make_series([1.0, 2.0, 3.0, 4.0])
        result = ema(ser, period=3)
        assert result.iloc[2] == pytest.approx(2.25)
        assert result.iloc[3] == pytest.approx(3.125)


class TestRSI:
    def test_empty_series_returns_empty(self):
        assert rsi(pd.Series([], dtype=float), period=3).empty

    def test_all_gains_rsi_is_100(self):
        ser = _make_series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        result = rsi(ser, period=3)
        assert result.iloc[3:].dropna().eq(100.0).all()

    def test_all_losses_rsi_is_0(self):
        ser = _make_series([8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0])
        result = rsi(ser, period=3)
        assert result.iloc[3:].dropna().eq(0.0).all()

    def test_flat_series_no_movement_rsi_is_100(self):
        # gain=0, loss=0 -> avg_loss==0 -> RSI 100 (kural: hareket yoksa "kayıp yok" kabul edilir)
        ser = _make_series([5.0] * 10)
        result = rsi(ser, period=3)
        assert result.iloc[3:].dropna().eq(100.0).all()

    def test_rsi_bounded_between_0_and_100(self):
        ser = _make_series([1.0, 3.0, 2.0, 5.0, 4.0, 8.0, 6.0, 9.0, 7.0, 12.0])
        result = rsi(ser, period=3).dropna()
        assert (result >= 0.0).all()
        assert (result <= 100.0).all()


class TestMACD:
    def test_empty_series_returns_empty(self):
        macd_line, signal_line, histogram = macd(pd.Series([], dtype=float))
        assert macd_line.empty and signal_line.empty and histogram.empty

    def test_warmup_before_slow_period_is_nan(self):
        ser = _make_series([float(i) for i in range(1, 20)])
        macd_line, signal_line, histogram = macd(ser, fast_period=3, slow_period=6, signal_period=2)
        assert macd_line.iloc[0:5].isna().all()
        assert macd_line.iloc[5:].notna().all()

    def test_histogram_equals_macd_minus_signal(self):
        ser = _make_series([float(i) for i in range(1, 40)])
        macd_line, signal_line, histogram = macd(ser, fast_period=3, slow_period=6, signal_period=2)
        diff = (histogram - (macd_line - signal_line)).dropna()
        assert (diff.abs() < 1e-9).all()

    def test_rising_series_macd_is_positive(self):
        # sürekli yükselen seri -> hızlı EMA yavaş EMA'nın üstünde -> MACD > 0
        ser = _make_series([float(i) for i in range(1, 60)])
        macd_line, _, _ = macd(ser, fast_period=12, slow_period=26, signal_period=9)
        assert (macd_line.dropna() > 0).all()


class TestBollingerBands:
    def test_empty_series_returns_empty(self):
        upper, middle, lower = bollinger_bands(pd.Series([], dtype=float), period=3)
        assert upper.empty and middle.empty and lower.empty

    def test_known_values(self):
        ser = _make_series([1.0, 2.0, 3.0, 4.0, 5.0])
        upper, middle, lower = bollinger_bands(ser, period=3, num_std=2.0)

        assert middle.iloc[2] == pytest.approx(2.0)
        assert upper.iloc[2] == pytest.approx(2.0 + 2 * 0.8164966)
        assert lower.iloc[2] == pytest.approx(2.0 - 2 * 0.8164966)

    def test_flat_series_bands_collapse_to_middle(self):
        ser = _make_series([5.0] * 10)
        upper, middle, lower = bollinger_bands(ser, period=3)
        assert (upper.dropna() == middle.dropna()).all()
        assert (lower.dropna() == middle.dropna()).all()


class TestATR:
    def test_empty_series_returns_empty(self):
        empty = pd.Series([], dtype=float)
        assert atr(empty, empty, empty, period=3).empty

    def test_known_values(self):
        highs = _make_series([10.0, 11.0, 12.0, 11.0, 13.0])
        lows = _make_series([9.0, 9.0, 10.0, 9.0, 10.0])
        closes = _make_series([9.5, 10.5, 11.0, 10.0, 12.0])

        result = atr(highs, lows, closes, period=3)

        assert result.iloc[0:2].isna().all()
        assert result.iloc[2] == pytest.approx(1.5556, abs=1e-3)
        assert result.iloc[3] == pytest.approx(1.7037, abs=1e-3)
        assert result.iloc[4] == pytest.approx(2.1358, abs=1e-3)

    def test_atr_is_never_negative(self):
        highs = _make_series([10.0, 9.0, 11.0, 8.0, 12.0, 7.0])
        lows = _make_series([8.0, 7.0, 9.0, 6.0, 10.0, 5.0])
        closes = _make_series([9.0, 8.0, 10.0, 7.0, 11.0, 6.0])
        result = atr(highs, lows, closes, period=3).dropna()
        assert (result >= 0).all()


class TestStochasticOscillator:
    def test_empty_series_returns_empty(self):
        empty = pd.Series([], dtype=float)
        percent_k, percent_d = stochastic_oscillator(empty, empty, empty, k_period=3, d_period=2)
        assert percent_k.empty and percent_d.empty

    def test_known_values(self):
        highs = _make_series([10.0, 11.0, 12.0, 11.0, 9.0])
        lows = _make_series([8.0, 9.0, 10.0, 8.0, 7.0])
        closes = _make_series([9.0, 10.0, 12.0, 8.0, 7.0])

        percent_k, percent_d = stochastic_oscillator(highs, lows, closes, k_period=3, d_period=3)

        assert percent_k.iloc[2] == pytest.approx(100.0)  # close == highest high in window
        assert percent_k.iloc[3] == pytest.approx(0.0)    # close == lowest low in window
        assert percent_k.iloc[4] == pytest.approx(0.0)
        assert percent_d.iloc[4] == pytest.approx(100.0 / 3, abs=1e-3)

    def test_flat_series_percent_k_is_neutral_50(self):
        ser = _make_series([5.0] * 10)
        percent_k, _ = stochastic_oscillator(ser, ser, ser, k_period=3, d_period=2)
        assert (percent_k.dropna() == 50.0).all()

    def test_percent_k_bounded_between_0_and_100(self):
        highs = _make_series([10.0, 9.0, 11.0, 8.0, 12.0, 7.0, 13.0])
        lows = _make_series([8.0, 7.0, 9.0, 6.0, 10.0, 5.0, 11.0])
        closes = _make_series([9.0, 8.0, 10.0, 7.0, 11.0, 6.0, 12.0])
        percent_k, _ = stochastic_oscillator(highs, lows, closes, k_period=3, d_period=2)
        result = percent_k.dropna()
        assert (result >= 0.0).all()
        assert (result <= 100.0).all()


class TestCCI:
    def test_empty_series_returns_empty(self):
        empty = pd.Series([], dtype=float)
        assert cci(empty, empty, empty, period=3).empty

    def test_flat_series_cci_is_zero(self):
        ser = _make_series([100.0] * 10)
        result = cci(ser, ser, ser, period=3)
        assert (result.dropna() == 0.0).all()

    def test_rising_series_cci_is_positive(self):
        highs = _make_series([float(i) + 1 for i in range(1, 30)])
        lows = _make_series([float(i) - 1 for i in range(1, 30)])
        closes = _make_series([float(i) for i in range(1, 30)])
        result = cci(highs, lows, closes, period=5).dropna()
        assert (result > 0).all()

    def test_falling_series_cci_is_negative(self):
        values = list(range(30, 1, -1))
        highs = _make_series([float(v) + 1 for v in values])
        lows = _make_series([float(v) - 1 for v in values])
        closes = _make_series([float(v) for v in values])
        result = cci(highs, lows, closes, period=5).dropna()
        assert (result < 0).all()


class TestVWAP:
    def test_empty_series_returns_empty(self):
        empty = pd.Series([], dtype=float)
        assert vwap(empty, empty, empty, empty, period=3).empty

    def test_equal_volumes_matches_simple_average(self):
        highs = _make_series([10.0, 11.0, 12.0, 13.0, 14.0])
        lows = _make_series([8.0, 9.0, 10.0, 11.0, 12.0])
        closes = _make_series([9.0, 10.0, 11.0, 12.0, 13.0])
        volumes = _make_series([100.0] * 5)

        result = vwap(highs, lows, closes, volumes, period=3)

        assert result.iloc[0:2].isna().all()
        assert result.iloc[2] == pytest.approx(10.0)
        assert result.iloc[3] == pytest.approx(11.0)
        assert result.iloc[4] == pytest.approx(12.0)

    def test_heavier_volume_pulls_vwap_toward_its_price(self):
        highs = _make_series([10.0, 20.0])
        lows = _make_series([10.0, 20.0])
        closes = _make_series([10.0, 20.0])
        volumes = _make_series([1.0, 99.0])

        result = vwap(highs, lows, closes, volumes, period=2)

        expected = (10.0 * 1.0 + 20.0 * 99.0) / 100.0
        assert result.iloc[1] == pytest.approx(expected)
        assert result.iloc[1] > 15.0  # basit ortalamadan (15.0) yüksek hacim ağırlıklı fiyata kaymalı


class TestOBV:
    def test_empty_series_returns_empty(self):
        empty = pd.Series([], dtype=float)
        assert obv(empty, empty).empty

    def test_known_values(self):
        closes = _make_series([10.0, 11.0, 10.0, 10.0, 12.0])
        volumes = _make_series([100.0, 200.0, 150.0, 50.0, 300.0])

        result = obv(closes, volumes)

        assert result.tolist() == pytest.approx([0.0, 200.0, 50.0, 50.0, 350.0])

    def test_monotonically_rising_series_obv_is_non_decreasing(self):
        closes = _make_series([float(i) for i in range(1, 20)])
        volumes = _make_series([100.0] * 19)
        result = obv(closes, volumes)
        assert (result.diff().dropna() >= 0).all()
