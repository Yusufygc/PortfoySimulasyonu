"""simulate_dca — saf DCA backtest hesabı testleri."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.application.services.simulation.dca_backtest import (
    equal_weights,
    monthly_contribution_dates,
    simulate_dca,
)


class TestSimulateDcaEdgeCases:
    def test_empty_price_series_returns_empty_result(self):
        result = simulate_dca({}, ["A"], {"A": 1.0}, Decimal("1000"), [])

        assert result.portfolio_value_series == {}
        assert result.total_invested == Decimal("0")
        assert result.final_value == Decimal("0")
        assert result.total_return_pct is None
        assert result.contribution_count == 0

    def test_no_contribution_dates_returns_empty_result(self):
        price_series = {date(2024, 1, 1): {"A": Decimal("100")}}
        result = simulate_dca(price_series, ["A"], {"A": 1.0}, Decimal("1000"), [])
        assert result.contribution_count == 0


class TestSimulateDcaSingleTicker:
    def test_flat_price_gives_zero_return(self):
        price_series = {
            date(2024, 1, 1): {"A": Decimal("100")},
            date(2024, 2, 1): {"A": Decimal("100")},
        }
        result = simulate_dca(
            price_series, ["A"], {"A": 1.0}, Decimal("1000"),
            contribution_dates=[date(2024, 1, 1), date(2024, 2, 1)],
        )

        assert result.total_invested == Decimal("2000")
        assert result.contribution_count == 2
        assert result.shares_by_ticker["A"] == Decimal("20")  # 1000/100 iki kez
        assert result.final_value == Decimal("2000")
        assert result.total_return_pct == pytest.approx(0.0)

    def test_rising_price_gives_positive_return(self):
        price_series = {
            date(2024, 1, 1): {"A": Decimal("100")},
            date(2024, 2, 1): {"A": Decimal("110")},
        }
        result = simulate_dca(
            price_series, ["A"], {"A": 1.0}, Decimal("1000"),
            contribution_dates=[date(2024, 1, 1)],
        )

        assert result.total_invested == Decimal("1000")
        assert result.shares_by_ticker["A"] == Decimal("10")
        assert result.final_value == Decimal("1100")
        assert result.total_return_pct == pytest.approx(10.0)

    def test_value_series_excludes_dates_before_first_contribution(self):
        price_series = {
            date(2024, 1, 1): {"A": Decimal("100")},
            date(2024, 2, 1): {"A": Decimal("105")},
            date(2024, 3, 1): {"A": Decimal("110")},
        }
        result = simulate_dca(
            price_series, ["A"], {"A": 1.0}, Decimal("1000"),
            contribution_dates=[date(2024, 2, 1)],
        )
        assert date(2024, 1, 1) not in result.portfolio_value_series
        assert date(2024, 2, 1) in result.portfolio_value_series
        assert date(2024, 3, 1) in result.portfolio_value_series


class TestSimulateDcaMultipleTickers:
    def test_weighted_split_across_two_tickers(self):
        price_series = {date(2024, 1, 1): {"A": Decimal("100"), "B": Decimal("50")}}
        result = simulate_dca(
            price_series, ["A", "B"], {"A": 0.6, "B": 0.4}, Decimal("1000"),
            contribution_dates=[date(2024, 1, 1)],
        )

        assert result.shares_by_ticker["A"] == Decimal("6")   # 600/100
        assert result.shares_by_ticker["B"] == Decimal("8")   # 400/50
        assert result.final_value == Decimal("1000")
        assert result.total_invested == Decimal("1000")


class TestSimulateDcaCarryForward:
    def test_missing_price_on_contribution_date_uses_last_known_price(self):
        price_series = {
            date(2024, 1, 1): {"A": Decimal("100")},
            date(2024, 1, 2): {},  # o gün fiyat yok ama contribution bu tarihte
        }
        result = simulate_dca(
            price_series, ["A"], {"A": 1.0}, Decimal("1000"),
            contribution_dates=[date(2024, 1, 2)],
        )

        assert result.contribution_count == 1
        assert result.shares_by_ticker["A"] == Decimal("10")  # 1000/100 (carry-forward)
        assert result.portfolio_value_series[date(2024, 1, 2)] == Decimal("1000")

    def test_ticker_with_no_price_data_is_simply_not_invested(self):
        # "GHOST" hiçbir tarihte fiyat almıyor -> payına ayrılan tutar hiç yatırılmaz.
        price_series = {date(2024, 1, 1): {"A": Decimal("100")}}
        result = simulate_dca(
            price_series, ["A", "GHOST"], {"A": 0.5, "GHOST": 0.5}, Decimal("1000"),
            contribution_dates=[date(2024, 1, 1)],
        )

        assert result.shares_by_ticker["GHOST"] == Decimal("0")
        assert result.total_invested == Decimal("500")  # sadece A'nın payı yatırıldı
        assert result.shares_by_ticker["A"] == Decimal("5")  # 500/100


class TestEqualWeights:
    def test_empty_tickers_returns_empty_dict(self):
        assert equal_weights([]) == {}

    def test_splits_evenly(self):
        result = equal_weights(["A", "B", "C", "D"])
        assert result == {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}


class TestMonthlyContributionDates:
    def test_empty_input_returns_empty_list(self):
        assert monthly_contribution_dates([]) == []

    def test_picks_earliest_date_per_month(self):
        dates = [
            date(2024, 1, 15), date(2024, 1, 3), date(2024, 1, 20),
            date(2024, 2, 10), date(2024, 2, 2),
        ]
        result = monthly_contribution_dates(dates)
        assert result == [date(2024, 1, 3), date(2024, 2, 2)]

    def test_skips_months_with_no_data(self):
        # Mart verisi yok -> sadece Ocak ve Nisan için katkı tarihi üretilir.
        dates = [date(2024, 1, 5), date(2024, 4, 8)]
        result = monthly_contribution_dates(dates)
        assert result == [date(2024, 1, 5), date(2024, 4, 8)]
