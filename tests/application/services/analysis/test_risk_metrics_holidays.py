"""Tatil günleri (iki seride de önceki değer taşınmış) eşleştirilmiş getirilere sıfır getiri olarak girmemeli."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from src.application.services.analysis.risk_metrics import compute_beta, compute_r_squared, compute_tracking_error

P = [100, 102, 101, 104, 103, 106, 105, 108]
B = [100, 101, 100.5, 102, 101.5, 103, 102.6, 104]


def _series(values, holidays=()):
    """Hafta içi günler; `holidays` sırasındaki noktalardan sonra değer taşınan bir gün eklenir."""
    out, day = {}, date(2026, 3, 2)
    for i, value in enumerate(values):
        out[day] = D(str(value))
        day += timedelta(days=1 if day.weekday() < 4 else 3)
        if i in holidays:
            out[day] = D(str(value))  # bayram: fiyat taşındı
            day += timedelta(days=1 if day.weekday() < 4 else 3)
    return out


@pytest.mark.parametrize("metric", [compute_beta, compute_r_squared, compute_tracking_error])
def test_holiday_carry_does_not_change_paired_metrics(metric):
    plain = metric(_series(P), _series(B))
    with_holidays = metric(_series(P, holidays=(1, 4)), _series(B, holidays=(1, 4)))
    assert with_holidays == pytest.approx(plain)
