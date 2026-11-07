from datetime import date

from src.infrastructure.market_data.bar_quality import is_flat_zero_volume, is_ghost_bar


def test_holiday_bar_is_ghost_even_with_volume():
    assert is_ghost_bar(date(2026, 5, 27), (10, 11, 9, 10.5, 1000))  # Kurban Bayramı 2026


def test_flat_zero_volume_bar_is_ghost():
    assert is_ghost_bar(date(2025, 5, 8), (7.25, 7.25, 7.25, 7.25, 0))
    assert is_flat_zero_volume((7.25, 7.25, 7.25, 7.25, 0))


def test_real_bar_and_pre_calendar_holiday_are_kept():
    assert not is_ghost_bar(date(2025, 5, 9), (214.7, 226.9, 207.0, 215.4, 3643667))
    assert not is_ghost_bar(date(2016, 7, 15), (10, 11, 9, 10.5, 1000))  # 15 Temmuz 2017 öncesi işlem günü


def test_missing_values_are_not_flat():
    assert not is_flat_zero_volume((None, 1, 1, 1, 0))
    assert not is_flat_zero_volume((float("nan"), 1, 1, 1, 0))
