"""detect_crosses saf vektörel hesap testleri."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from src.application.services.analysis.technical.golden_cross import detect_crosses
from src.domain.models.golden_cross_event import CrossType


def _make_series(values: list[float], start: date = date(2020, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(values, index=idx)


class TestInsufficientData:
    def test_empty_series_returns_empty(self):
        assert detect_crosses(pd.Series([], dtype=float)) == []

    def test_under_long_returns_empty(self):
        ser = _make_series([100.0] * 100)
        assert detect_crosses(ser, short=20, long=50) == []

    def test_exactly_long_returns_empty(self):
        # n_rows == long → SMA(long) tek değer üretir, sign.shift(1) NaN → cross yok
        ser = _make_series([100.0] * 50)
        assert detect_crosses(ser, short=20, long=50) == []


class TestCrossDetection:
    def test_no_cross_flat_series(self):
        ser = _make_series([100.0] * 300)
        assert detect_crosses(ser, short=20, long=50) == []

    def test_golden_cross_detected(self):
        """short MA önce long altında, sonra üstüne çıkar → 1 Golden Cross."""
        # 200 düz fiyat sonra 100 gün artan → short MA önce long altında, sonra üstünde
        flat = [100.0] * 100
        rising = [100.0 + i for i in range(1, 121)]
        ser = _make_series(flat + rising)
        crosses = detect_crosses(ser, short=20, long=50)
        assert len(crosses) >= 1
        assert any(c.cross_type == CrossType.GOLDEN for c in crosses)

    def test_death_cross_detected(self):
        """Tersine: önce yüksek sonra düşen → Death Cross."""
        rising = [100.0 + i for i in range(1, 121)]
        falling = [220.0 - i for i in range(1, 121)]
        ser = _make_series(rising + falling)
        crosses = detect_crosses(ser, short=20, long=50)
        assert any(c.cross_type == CrossType.DEATH for c in crosses)

    def test_cross_returns_correct_fields(self):
        flat = [100.0] * 100
        rising = [100.0 + i for i in range(1, 121)]
        ser = _make_series(flat + rising)
        crosses = detect_crosses(ser, short=20, long=50)
        c = next(c for c in crosses if c.cross_type == CrossType.GOLDEN)
        assert isinstance(c.cross_date, date)
        assert isinstance(c.short_ma, Decimal)
        assert isinstance(c.long_ma, Decimal)
        assert isinstance(c.close_price, Decimal)
        assert c.close_price > 0

    def test_multiple_crosses_chronological(self):
        # 50 düz + 50 yükseliş + 50 düşüş + 50 yükseliş → 2-3 cross
        flat = [100.0] * 80
        up1 = [100.0 + i for i in range(1, 61)]
        dn  = [160.0 - i for i in range(1, 81)]
        up2 = [80.0 + i for i in range(1, 121)]
        ser = _make_series(flat + up1 + dn + up2)
        crosses = detect_crosses(ser, short=20, long=50)
        # Tarihler artan sırada gelmeli
        dates = [c.cross_date for c in crosses]
        assert dates == sorted(dates)
        # En az 2 cross (golden→death veya death→golden)
        assert len(crosses) >= 2
