"""Nakit izlenen seride nakdi aşan alım ve başlangıç nakdi kuralları.

- Mevcut nakdi aşan alımın karşılanmayan kısmı dış sermaye girişidir; getiri olarak görünmez (TWR sabit kalır).
- Başlangıç nakdi, gün içi döngüyle aynı kuralla (ücret dahil, kronolojik) hesaplanır; seri başlangıç gününden bağımsızdır.
"""
from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.portfolio_series_builder import PortfolioSeriesBuilder, PortfolioSeriesRequest
from src.application.services.analysis.unified_series_builder import UnifiedSeriesBuilder, UnifiedSeriesDeps
from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade

D = Decimal
DAY1 = date(2026, 3, 2)
DAYS = [DAY1 + timedelta(days=i) for i in range(5)]


def _deposit(amount, day):
    return CashMovement(id=None, movement_date=day, movement_time=None, type=CashMovementType.DEPOSIT, amount=D(amount))


def _buy(qty, price, day, fee="0"):
    return Trade.create_buy(stock_id=1, trade_date=day, quantity=qty, price=D(price), fee=D(fee))


def _bist_series(trades, movements, closes, start, end):
    price_repo = MagicMock()
    price_repo.get_price_series.side_effect = lambda _sid, s, e: [
        SimpleNamespace(price_date=d, close_price=D(c)) for d, c in sorted(closes.items()) if s <= d <= e
    ]
    price_repo.get_last_price_before.side_effect = lambda _sid, day: next(
        (SimpleNamespace(close_price=D(c)) for d, c in sorted(closes.items(), reverse=True) if d < day), None
    )
    request = PortfolioSeriesRequest(
        trades=trades, cash_movements=movements, stock_ids=[1], ticker_map={1: "AAA"},
        start_date=start, end_date=end, portfolio=Portfolio.from_trades(trades),
    )
    values, twr, _, _ = PortfolioSeriesBuilder(price_repo, MagicMock()).compute_portfolio_series(request)
    return values, twr


class _UnifiedFakes:
    """UnifiedSeriesBuilder'ın kullandığı depo yüzeyi: yalnızca BIST işlemi, nakit ve sabit kur."""

    def __init__(self, trades, movements, closes):
        self._trades, self._movements, self._closes = trades, movements, closes

    def get_all_trades(self):
        return list(self._trades)

    def get_all_movements(self):
        return list(self._movements)

    def list_trades(self, asset_id=None):
        return []

    def list_all(self):
        return []

    def list_assets(self, active_only=True):
        return []

    def get_price_series(self, stock_id, start, end):
        return [SimpleNamespace(price_date=d, close_price=D(c)) for d, c in sorted(self._closes.items()) if start <= d <= end]

    def get_last_price_before(self, stock_id, day):
        older = [(d, c) for d, c in self._closes.items() if d < day]
        return SimpleNamespace(close_price=D(max(older)[1])) if older else None

    def get_rates(self, base, quote, start=None, end=None):
        return []

    def get_rate_on_or_before(self, base, quote, day):
        return None

    def get_ticker_map_for_stock_ids(self, ids):
        return {i: f"T{i}.IS" for i in ids}

    def build(self, start, end):
        return UnifiedSeriesBuilder(UnifiedSeriesDeps(*([self] * 9))).build(start, end)


FLAT = {d: "10" for d in DAYS}


class TestUnfundedBuyIsExternalInflow:
    def _scenario(self):
        trades = [_buy(100, "10", DAYS[0]), _buy(500, "10", DAYS[2])]   # ikinci alımda nakit yok
        movements = [_deposit("1000", DAYS[0])]
        return trades, movements

    def test_bist_series_twr_stays_flat(self):
        trades, movements = self._scenario()
        values, twr = _bist_series(trades, movements, FLAT, DAYS[0], DAYS[-1])
        assert values[DAYS[2]] == D("6000")                       # 600 lot x 10, nakit 0
        assert all(twr[d] == D("100") for d in DAYS)

    def test_unified_series_twr_stays_flat(self):
        trades, movements = self._scenario()
        series = _UnifiedFakes(trades, movements, FLAT).build(DAYS[0], DAYS[-1])
        assert series.values[DAYS[2]] == D("6000")
        assert all(series.twr[d] == D("100") for d in DAYS)


class TestInitialCashMatchesDailyLoop:
    def test_fee_is_deducted_and_value_independent_of_start_date(self):
        jan5, jan6 = date(2026, 1, 5), date(2026, 1, 6)
        trades = [_buy(100, "10", jan5, fee="50")]
        movements = [_deposit("2000", jan5)]
        closes = {jan5: "10", jan6: "10"}
        from_jan5, _ = _bist_series(trades, movements, closes, jan5, jan6)
        from_jan6, _ = _bist_series(trades, movements, closes, jan6, jan6)
        assert from_jan5[jan6] == D("1950")                       # 2000 - 1050 + 100 x 10
        assert from_jan6[jan6] == from_jan5[jan6]

    def test_history_is_processed_chronologically_across_days(self):
        # Gün 1: 1000 yatır, 1000'lik al. Gün 2: nakit yokken 500'lük al (dışarıdan gelir). Gün 3: 500 yatır.
        trades = [_buy(100, "10", DAYS[0]), _buy(50, "10", DAYS[1])]
        movements = [_deposit("1000", DAYS[0]), _deposit("500", DAYS[2])]
        from_day1, _ = _bist_series(trades, movements, FLAT, DAYS[0], DAYS[4])
        from_day4, _ = _bist_series(trades, movements, FLAT, DAYS[3], DAYS[4])
        assert from_day1[DAYS[4]] == D("2000")                    # 150 lot x 10 + 500 nakit
        assert from_day4[DAYS[4]] == from_day1[DAYS[4]]
