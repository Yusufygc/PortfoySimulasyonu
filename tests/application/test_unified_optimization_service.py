"""Birleşik optimizasyon girdisi: TL fiyat matrisi, ortak geçmiş, kesirli miktar planı ve pozisyon yeterliliği."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.application.services.planning.frontier_simulation import calculate_rebalance_plan
from src.application.services.planning.unified_optimization_service import (
    UnifiedOptimizationService,
    asset_try_series,
    combine_prices,
    trim_to_common_history,
)
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.unified_portfolio import AllocationClass, HoldingValuation

D = Decimal
TODAY = date.today()


def holding(symbol, cls, quantity, value, ref_id=None):
    return HoldingValuation(key=f"{cls.value}:{symbol}", symbol=symbol, name=symbol, allocation_class=cls, quantity=D(quantity),
                            native_currency="TRY", cost_native=D(value), cost_try=D(value), value_try=D(value), ref_id=ref_id)


def btc():
    return Asset(1, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD")


def gold_gram():
    return Asset(2, "XAU", "Altın (gram)", AssetClass.PRECIOUS_METAL, "USD", "GC=F", unit=AssetUnit.GRAM, trade_currency="TRY")


class TestAssetTrySeries:
    def test_usd_close_is_converted_with_forward_filled_rate(self):
        days = [TODAY - timedelta(days=3), TODAY - timedelta(days=2), TODAY - timedelta(days=1)]
        closes = {d: D("100") for d in days}
        rates = {days[0]: D("30"), days[2]: D("33")}                    # ortadaki gün kursu yok -> önceki kur

        series = asset_try_series(btc(), closes, rates)

        assert list(series.values) == [3000.0, 3000.0, 3300.0]

    def test_gram_gold_uses_ounce_to_gram_conversion(self):
        closes = {TODAY: D("3110.35")}                                   # USD/ons

        series = asset_try_series(gold_gram(), closes, {TODAY: D("30")})

        assert series.iloc[0] == pytest.approx(3000.0, rel=1e-4)         # 100 USD/g x 30

    def test_missing_prices_or_rates_yield_empty_series(self):
        assert asset_try_series(btc(), {}, {TODAY: D("30")}).empty
        assert asset_try_series(btc(), {TODAY: D("100")}, {}).empty


class TestCombineAndTrim:
    @staticmethod
    def _bist(days):
        return pd.DataFrame({"AAA": np.linspace(10, 20, len(days))}, index=pd.to_datetime(days))

    def test_asset_series_are_aligned_to_bist_days_with_forward_fill(self):
        bist = self._bist(["2026-03-02", "2026-03-03", "2026-03-04"])
        crypto = pd.Series([100.0, 110.0], index=pd.to_datetime(["2026-03-01", "2026-03-04"]))   # pazar günü + çarşamba

        frame = combine_prices(bist, {"BTC": crypto})

        assert list(frame.index) == list(bist.index)
        assert list(frame["BTC"]) == [100.0, 100.0, 110.0]                # BIST günlerine ileri taşınır

    def test_without_bist_the_union_of_asset_days_is_used(self):
        a = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-03-01", "2026-03-03"]))

        frame = combine_prices(pd.DataFrame(), {"A": a})

        assert list(frame.columns) == ["A"] and len(frame) == 2

    def test_trim_drops_the_shortest_history_when_common_window_is_too_short(self):
        index = pd.date_range("2026-01-01", periods=100)
        frame = pd.DataFrame({"LONG": np.arange(100.0) + 1, "NEW": np.nan}, index=index)
        frame.loc[index[80]:, "NEW"] = 5.0                                 # yalnızca 20 günlük geçmiş

        trimmed = trim_to_common_history(frame, min_rows=60)

        assert list(trimmed.columns) == ["LONG"] and len(trimmed) == 100


class TestRebalancePlanFractional:
    def test_asset_symbols_get_fractional_quantities_and_bist_stays_whole(self):
        plan = calculate_rebalance_plan(
            total_portfolio_value=100000.0,
            current_weights={"AAA": 50.0, "BTC": 50.0},
            optimal_weights={"AAA": 30.0, "BTC": 70.0},
            last_prices={"AAA": 12.5, "BTC": 2_000_000.0},
            fractional={"BTC"},
        )

        by_symbol = {row["symbol"]: row for row in plan}
        assert by_symbol["AAA"]["estShares"] == 1600 and isinstance(by_symbol["AAA"]["estShares"], int)
        assert by_symbol["BTC"]["estShares"] == pytest.approx(0.01)       # 20.000 TL / 2.000.000


class FakeOptimizer:
    def __init__(self, bist_df):
        self._bist_df = bist_df
        self.calls = []

    def _get_historical_prices(self, tickers, days):
        return self._bist_df[[t for t in tickers if t in self._bist_df.columns]]

    def _optimize(self, tickers, weights, policy=None, price_df=None):
        self.calls.append((list(tickers), list(np.round(weights, 4)), price_df))
        return "SONUC"


class TestService:
    @staticmethod
    def _service(holdings, optimizer, asset_rows=None):
        unified = SimpleNamespace(get_summary=lambda currency: SimpleNamespace(holdings=tuple(holdings)))
        assets = {1: btc()}
        price_repo = SimpleNamespace(get_daily_prices=lambda aid, start, end: [
            SimpleNamespace(price_date=d, close_price=p) for d, p in (asset_rows or {}).get(aid, [])])
        fx_repo = SimpleNamespace(get_rates=lambda base, quote, start, end: [
            SimpleNamespace(rate_date=TODAY - timedelta(days=i), rate=D("30")) for i in range(150)])
        return UnifiedOptimizationService(unified, optimizer, SimpleNamespace(get_asset=assets.get), price_repo, fx_repo)

    def test_needs_at_least_two_holdings(self):
        service = self._service([holding("AAA", AllocationClass.BIST_STOCK, 10, 1000)], FakeOptimizer(pd.DataFrame()))

        with pytest.raises(ValueError, match="en az 2"):
            service.load_universe()

    def test_universe_mixes_bist_and_assets_in_try_with_current_weights(self):
        index = pd.date_range(TODAY - timedelta(days=149), TODAY, freq="B")
        bist = pd.DataFrame({"AAA": np.linspace(10, 20, len(index)), "BBB": np.linspace(5, 9, len(index))}, index=index)
        rows = {1: [(TODAY - timedelta(days=i), D("100") + i) for i in range(150)]}
        holdings = [holding("AAA", AllocationClass.BIST_STOCK, 100, 6000), holding("BBB", AllocationClass.BIST_STOCK, 100, 2000),
                    holding("BTC", AllocationClass.CRYPTO, "0.5", 2000, ref_id=1)]
        optimizer = FakeOptimizer(bist)
        service = self._service(holdings, optimizer, rows)

        universe = service.load_universe()
        result = service.optimize(universe)

        assert result == "SONUC"
        assert set(universe.price_df.columns) == {"AAA", "BBB", "BTC"}
        assert universe.fractional == {"BTC"} and universe.last_prices_try["BTC"] == pytest.approx(4000.0)   # 2.000 / 0,5
        tickers, weights, frame = optimizer.calls[0]
        assert tickers == ["AAA", "BBB", "BTC"] and weights == [0.6, 0.2, 0.2]
        assert frame is universe.price_df
