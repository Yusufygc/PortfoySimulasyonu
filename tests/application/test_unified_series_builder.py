"""Birleşik TWR/değer serisi: dış akış kuralları, döviz, nakde bağlı ve eski varlık işlemleri, gram altın, pozisyon özeti."""
from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.analysis.unified_series_builder import UnifiedSeriesBuilder, UnifiedSeriesDeps
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.cash_movement import CashMovement
from src.domain.models.fx_conversion import FxConversion, FxSide
from src.domain.models.trade import Trade, TradeSide

D = Decimal
START, END = date(2026, 3, 2), date(2026, 3, 6)          # pazartesi - cuma
DAYS = [date(2026, 3, day) for day in range(2, 7)]


class FakeRepos:
    """Gerçek depoların kullanılan yüzeyi; veriler listelerde tutulur."""

    def __init__(self):
        self.trades, self.movements, self.asset_trades, self.conversions = [], [], [], []
        self.assets = {}
        self.stock_prices = {}      # stock_id -> {gün: fiyat}
        self.asset_prices = {}      # asset_id -> {gün: fiyat}
        self.fx = {}                # {gün: USDTRY}

    # --- portfolio_repo / cash_repo / asset repos ---
    def get_all_trades(self):
        return list(self.trades)

    def get_all_movements(self):
        return list(self.movements)

    def list_trades(self, asset_id=None):
        return list(self.asset_trades)

    def list_all(self):
        return list(self.conversions)

    def list_assets(self, active_only=True):
        return list(self.assets.values())

    # --- fiyatlar ---
    def get_price_series(self, stock_id, start, end):
        return [SimpleNamespace(price_date=d, close_price=p) for d, p in sorted(self.stock_prices.get(stock_id, {}).items()) if start <= d <= end]

    def get_last_price_before(self, stock_id, day):
        older = [(d, p) for d, p in self.stock_prices.get(stock_id, {}).items() if d < day]
        return SimpleNamespace(close_price=max(older)[1]) if older else None

    def get_daily_prices(self, asset_id, start=None, end=None):
        return [SimpleNamespace(price_date=d, close_price=p) for d, p in sorted(self.asset_prices.get(asset_id, {}).items()) if start <= d <= end]

    def get_last_daily_price(self, asset_id, on_or_before=None):
        older = [(d, p) for d, p in self.asset_prices.get(asset_id, {}).items() if on_or_before is None or d <= on_or_before]
        return SimpleNamespace(close_price=max(older)[1]) if older else None

    def get_rates(self, base, quote, start=None, end=None):
        return [SimpleNamespace(rate_date=d, rate=r) for d, r in sorted(self.fx.items()) if start <= d <= end]

    def get_rate_on_or_before(self, base, quote, day):
        older = [(d, r) for d, r in self.fx.items() if d <= day]
        return SimpleNamespace(rate=max(older)[1]) if older else None

    def get_ticker_map_for_stock_ids(self, ids):
        return {i: f"T{i}.IS" for i in ids}

    def builder(self):
        return UnifiedSeriesBuilder(UnifiedSeriesDeps(self, self, self, self, self, self, self, self, self))


def flat_fx(repos, rate="40"):
    repos.fx = {d: D(rate) for d in DAYS}


def deposit(amount, day=DAYS[0]):
    return CashMovement.create_deposit(D(amount), day, time(9, 0))


def withdraw(amount, day):
    return CashMovement.create_withdraw(D(amount), day, time(9, 0))


def bist_buy(qty, price, day=DAYS[0], at=time(10, 0)):
    return Trade.create_buy(1, day, qty, D(price), at)


def usd_asset(symbol="BTC", asset_id=1, **options):
    return Asset(asset_id, symbol, symbol, AssetClass.CRYPTO, "USD", f"{symbol}-USD", **options)


def asset_buy(asset_id, qty, price, day, **extra):
    """Varlık alımı. `extra`: fx (varsayılan 40), linked (nakde bağlı, varsayılan True), at (saat)."""
    return AssetTrade(None, asset_id, day, extra.get("at", time(11, 0)), TradeSide.BUY, D(qty), D(price), D(extra.get("fx", "40")),
                      cash_linked=extra.get("linked", True))


def fx_buy(usd, rate, day):
    return FxConversion(None, day, time(9, 30), FxSide.BUY_USD, D(usd), D(rate))


@pytest.fixture
def repos():
    return FakeRepos()


class TestExternalFlows:
    def test_bist_only_with_deposit_matches_stock_return(self, repos):
        repos.movements = [deposit("10000")]
        repos.trades = [bist_buy(100, "50")]                       # 5.000 TL hisse + 5.000 TL nakit
        repos.stock_prices[1] = {d: D(p) for d, p in zip(DAYS, ("50", "50", "55", "55", "60"))}

        series = repos.builder().build(START, END)

        assert series.values[DAYS[-1]] == D("11000")               # 100 x 60 + 5.000 nakit
        assert series.twr[DAYS[-1]] == pytest.approx(D("110"))     # 10.000 -> 11.000, akış yok

    def test_withdrawal_is_an_outflow_not_a_loss(self, repos):
        repos.movements = [deposit("10000"), withdraw("4000", DAYS[2])]
        repos.fx = {}

        series = repos.builder().build(START, END)

        assert series.values[DAYS[-1]] == D("6000")
        assert series.twr[DAYS[-1]] == D("100")                    # yalnızca nakit; getiri yok

    def test_without_cash_history_trades_are_flows(self, repos):
        repos.trades = [bist_buy(100, "50", DAYS[1])]
        repos.stock_prices[1] = {d: D("50") for d in DAYS}

        series = repos.builder().build(START, END)

        assert series.values[DAYS[0]] == D("0")
        assert series.values[DAYS[-1]] == D("5000")                # nakit izlenmez; yalnızca pozisyon değeri
        assert series.twr[DAYS[-1]] == D("100")                    # alım dış akış sayılır; getiri sıfır


class TestFxAndAssets:
    def test_fx_conversion_is_internal_and_rate_move_is_return(self, repos):
        repos.movements = [deposit("100000")]
        repos.conversions = [fx_buy("1000", "40", DAYS[1])]
        repos.fx = {DAYS[0]: D("40"), DAYS[1]: D("40"), DAYS[2]: D("44"), DAYS[3]: D("44"), DAYS[4]: D("44")}

        series = repos.builder().build(START, END)

        assert series.values[DAYS[1]] == D("100000")               # çevirme değeri değiştirmez
        assert series.twr[DAYS[1]] == D("100")
        assert series.values[DAYS[2]] == D("104000")               # 1.000 USD x 44 + 60.000 TL
        assert series.twr[DAYS[2]] == pytest.approx(D("104"))      # kur artışı getiridir, akış değil

    def test_cash_linked_usd_asset_purchase_is_internal(self, repos):
        repos.movements = [deposit("100000")]
        repos.conversions = [fx_buy("1000", "40", DAYS[0])]
        repos.assets = {1: usd_asset()}
        repos.asset_trades = [asset_buy(1, "0.01", "50000", DAYS[1])]   # 500 USD
        repos.asset_prices[1] = {d: D(p) for d, p in zip(DAYS, ("50000", "50000", "55000", "55000", "55000"))}
        flat_fx(repos)

        series = repos.builder().build(START, END)

        assert series.values[DAYS[1]] == D("100000")               # 500 USD nakit -> 500 USD BTC
        assert series.twr[DAYS[1]] == D("100")
        assert series.values[DAYS[2]] == D("102000")               # BTC %10 arttı: +50 USD x 40
        assert series.twr[DAYS[2]] == pytest.approx(D("102"))

    def test_legacy_asset_purchase_is_an_inflow(self, repos):
        repos.movements = [deposit("100000")]
        repos.assets = {1: usd_asset()}
        repos.asset_trades = [asset_buy(1, "0.01", "50000", DAYS[1], linked=False)]   # nakde dokunmaz
        repos.asset_prices[1] = {d: D("50000") for d in DAYS}
        flat_fx(repos)

        series = repos.builder().build(START, END)

        assert series.values[DAYS[1]] == D("120000")               # 500 USD x 40 = 20.000 TL eklendi
        assert series.twr[DAYS[1]] == D("100")                     # dışarıdan giren sermaye getiri değil

    def test_gram_gold_is_valued_in_try_per_gram(self, repos):
        gold = Asset(2, "XAU", "Altın (gram)", AssetClass.PRECIOUS_METAL, "USD", "GC=F", unit=AssetUnit.GRAM, trade_currency="TRY")
        repos.movements = [deposit("100000")]
        repos.assets = {2: gold}
        repos.asset_trades = [asset_buy(2, "10", "3000", DAYS[0], fx="1")]   # 10 g x 3.000 TL
        repos.asset_prices[2] = {d: D("3110.35") for d in DAYS}                               # USD/ons
        flat_fx(repos, "30")

        series = repos.builder().build(START, END)

        # 3.110,35 USD/ons / 31,1035 = 100 USD/g x 30 = 3.000 TL/g -> 10 g = 30.000 TL; nakit 70.000 TL
        assert series.values[DAYS[-1]] == pytest.approx(D("100000"), abs=D("1"))
        assert series.twr[DAYS[-1]] == pytest.approx(D("100"), abs=D("0.01"))

    def test_missing_asset_price_falls_back_to_trade_value_with_warning(self, repos):
        repos.movements = [deposit("100000")]
        repos.assets = {1: usd_asset()}
        repos.asset_trades = [asset_buy(1, "0.01", "50000", DAYS[0], linked=False)]
        flat_fx(repos)                                             # fiyat serisi yok

        series = repos.builder().build(START, END)

        assert series.values[DAYS[-1]] == D("120000")              # işlem değeriyle değerlenir, düşüş yok
        assert any("BTC" in warning for warning in series.warnings)


class TestUnpricedBistPosition:
    """D-02: fiyat geçmişi olmayan BIST pozisyonu toplamdan sessizce düşmez; Portföyüm gibi ortalama maliyetle değerlenir."""

    def test_missing_bist_price_falls_back_to_average_cost_with_warning(self, repos):
        repos.movements = [deposit("100000")]
        repos.trades = [bist_buy(60, "260")]                      # kapanış serisi yok
        repos.stock_prices = {}

        series = repos.builder().build(START, END)

        assert series.values[DAYS[-1]] == D("100000")             # nakit 84.400 + pozisyon 15.600
        assert any("T1" in warning for warning in series.warnings)
        assert [item["label"] for item in series.holdings] == ["T1"]

    def test_fallback_uses_remaining_average_cost_after_partial_sell(self, repos):
        repos.movements = [deposit("100000")]
        repos.trades = [bist_buy(60, "260"), Trade.create_sell(1, DAYS[1], 20, D("300"), time(10, 0))]

        series = repos.builder().build(START, END)

        assert series.values[DAYS[-1]] == D("100000") + D("20") * D("300") - D("20") * D("260")   # 40 lot x 260 maliyet + nakit

    def test_priced_bist_position_has_no_warning(self, repos):
        repos.movements = [deposit("100000")]
        repos.trades = [bist_buy(60, "260")]
        repos.stock_prices = {1: {day: D("270") for day in DAYS}}

        series = repos.builder().build(START, END)

        assert series.values[DAYS[-1]] == D("100000") + D("600")
        assert series.warnings == []


class TestHoldingsSnapshot:
    def test_snapshot_lists_bist_and_asset_positions_with_weights_and_returns(self, repos):
        repos.movements = [deposit("100000")]
        repos.trades = [bist_buy(100, "50")]
        repos.stock_prices[1] = {d: D("60") for d in DAYS}          # +%20
        repos.assets = {1: usd_asset()}
        repos.conversions = [fx_buy("1000", "40", DAYS[0])]
        repos.asset_trades = [asset_buy(1, "0.01", "50000", DAYS[0])]
        repos.asset_prices[1] = {d: D("50000") for d in DAYS}
        flat_fx(repos)

        series = repos.builder().build(START, END)

        by_label = {item["label"]: item for item in series.holdings}
        assert set(by_label) == {"T1", "BTC"}                       # .IS soneki atılır; nakit yok
        assert by_label["T1"]["current_value"] == D("6000") and by_label["T1"]["return_pct"] == pytest.approx(20.0)
        assert by_label["BTC"]["current_value"] == D("20000") and by_label["BTC"]["return_pct"] == pytest.approx(0.0)
        assert by_label["T1"]["weight"] + by_label["BTC"]["weight"] == pytest.approx(100.0)

    def test_empty_when_no_events(self, repos):
        series = repos.builder().build(START, END)

        assert series.values == {} and series.twr == {} and series.holdings == []


class TestAnalysisServiceIntegration:
    """Tüm Varlıklar kaynağı: seçenek listesi, ilk tarih, rapor ve karşılaştırma serisi."""

    @staticmethod
    def _service(repos):
        from src.application.services.analysis import AnalysisService
        from src.application.services.analysis.analysis_service import AnalysisServiceDeps

        deps = AnalysisServiceDeps(repos, repos, repos, SimpleNamespace(get_price_series=lambda *a, **k: {}))
        return AnalysisService(deps, unified_builder=repos.builder())

    @staticmethod
    def _seed(repos):
        repos.movements = [deposit("100000")]
        repos.conversions = [fx_buy("1000", "40", DAYS[0])]
        repos.assets = {1: usd_asset()}
        repos.asset_trades = [asset_buy(1, "0.01", "50000", DAYS[0])]
        repos.asset_prices[1] = {d: D(p) for d, p in zip(DAYS, ("50000", "50000", "55000", "55000", "60000"))}
        flat_fx(repos)

    def test_source_is_listed_and_dates_include_asset_events(self, repos):
        self._seed(repos)
        service = self._service(repos)

        assert [(o.code, o.label) for o in service.get_portfolio_options()][:2] == [("dashboard", "Ana Portföy"), ("unified", "Tüm Varlıklar")]
        assert service.get_first_trade_date_for_source("unified") == DAYS[0]

    def test_risk_and_overview_use_unified_series_and_snapshot(self, repos):
        from src.application.services.analysis import AnalysisFilterState

        self._seed(repos)
        service = self._service(repos)

        payload = service.get_page_payload(AnalysisFilterState(start_date=START, end_date=END, portfolio_source="unified"))

        overview, risk = payload["overview"], payload["risk"]
        assert overview.portfolio_label == "Tüm Varlıklar"
        assert overview.period_return_pct == pytest.approx(4.0)       # 100.000 -> 104.000 TL (BTC 50.000 -> 60.000 USD); akış yok
        assert [item.label for item in risk.items] == ["BTC"] and risk.items[0].weight_pct == pytest.approx(100.0)
        assert risk.volatility_pct is not None

    def test_unified_is_available_as_a_comparison_series(self, repos):
        from src.application.services.analysis import AnalysisFilterState

        self._seed(repos)
        service = self._service(repos)
        state = AnalysisFilterState(start_date=START, end_date=END, portfolio_source="dashboard",
                                    comparison_portfolio_sources=["dashboard", "unified"])

        view = service.get_comparison_view(state)

        assert [series.code for series in view.comparison_portfolios] == ["unified"]
        assert len(view.comparison_portfolios[0].points) == len(DAYS)

    def test_source_is_hidden_without_a_builder(self, repos):
        from src.application.services.analysis import AnalysisService
        from src.application.services.analysis.analysis_service import AnalysisServiceDeps

        service = AnalysisService(AnalysisServiceDeps(repos, repos, repos, SimpleNamespace(get_price_series=lambda *a, **k: {})))

        assert [o.code for o in service.get_portfolio_options()] == ["dashboard"]


class TestUnifiedReturnService:
    """Haftalık/aylık getiri kartları: TWR oranı, akıştan etkilenmez."""

    @staticmethod
    def _returns(repos, end):
        from src.application.services.analysis.unified_return_service import UnifiedReturnService

        return UnifiedReturnService(repos.builder()).returns(end)

    def test_week_and_month_use_twr_so_deposits_do_not_count_as_return(self, repos):
        end = date(2026, 3, 31)
        repos.movements = [deposit("100000", date(2026, 2, 1)), deposit("100000", date(2026, 3, 28))]   # son hafta yeni para
        repos.conversions = [fx_buy("1000", "40", date(2026, 2, 2))]
        repos.fx = {date(2026, 2, 1) + timedelta(days=i): D("40") if i < 40 else D("44") for i in range(60)}   # kur 11 Mart'tan sonra 44

        weekly, monthly = self._returns(repos, end)

        assert weekly == pytest.approx(0.0, abs=1e-9)           # kur son 7 günde sabit; 28 Mart yatırması getiri değil
        assert monthly == pytest.approx(4.0)                    # 1.000 USD x (44 - 40) = 4.000 TL / 100.000 TL; yatırma hariç

    def test_empty_portfolio_has_no_return(self, repos):
        assert self._returns(repos, date(2026, 3, 31)) == (None, None)

    def test_portfolio_started_inside_the_period_is_measured_from_its_first_funded_day(self, repos):
        repos.movements = [deposit("100000", date(2026, 3, 20))]
        repos.conversions = [fx_buy("1000", "40", date(2026, 3, 20))]
        repos.fx = {date(2026, 3, 20) + timedelta(days=i): D("40") if i < 5 else D("44") for i in range(12)}   # 25 Mart'ta 44

        weekly, monthly = self._returns(repos, date(2026, 3, 31))

        assert weekly == pytest.approx(4.0) and monthly == pytest.approx(4.0)     # 7 günde ve açılıştan beri aynı +%4

    def test_single_funded_day_has_no_return(self, repos):
        repos.movements = [deposit("1000", date(2026, 3, 31))]

        assert self._returns(repos, date(2026, 3, 31)) == (None, None)
