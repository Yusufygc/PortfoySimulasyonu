"""UnifiedPortfolioService: BIST + varlık defteri birleşik TRY özeti (gerçek domain nesneleri, sahte kaynaklar)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

import pytest

from src.application.services.assets.asset_holdings_reader import AssetHoldingsReader
from src.application.services.assets.bist_holdings_reader import BistHoldingsReader
from src.application.services.assets.unified_portfolio_service import UnifiedPortfolioService
from src.application.services.market.current_price_resolver import ResolvedPrice
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.asset_position import AssetLedger
from src.domain.models.asset_price import AssetLatestPrice, AssetPrice
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.portfolio import Portfolio
from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.unified_portfolio import AllocationClass
from src.domain.units import TROY_OUNCE_GRAMS

D = Decimal
DAY = date(2026, 1, 5)
NOON = datetime(2026, 1, 5, 12, 0)


# ---------------- sahte kaynaklar ---------------- #


class FakePortfolioService:
    def __init__(self, trades: List[Trade], cash="0"):
        self._portfolio = Portfolio.from_trades(trades)
        self._cash = D(cash)

    def get_cash_balance(self):
        return self._cash

    def get_current_portfolio(self):
        return self._portfolio


class FakeStockLookup:
    def __init__(self, stocks: List[Stock]):
        self._stocks = {s.id: s for s in stocks}

    def get_stocks(self, ids):
        return {i: self._stocks[i] for i in ids if i in self._stocks}


class FakeResolver:
    def __init__(self, prices: Dict[int, str], changes: Optional[Dict[int, str]] = None):
        self._prices = {i: ResolvedPrice(D(p), DAY, "daily") for i, p in prices.items()}
        self._changes = {i: D(c) for i, c in (changes or {}).items()}

    def resolve(self, ids):
        return {i: self._prices[i] for i in ids if i in self._prices}

    def daily_change_pct(self, stock_id, resolved):
        return self._changes.get(stock_id)


class FakeLedgerService:
    def __init__(self, assets: List[Asset], trades: List[AssetTrade]):
        self._assets, self._trades = assets, trades

    def get_ledger(self):
        return AssetLedger.from_trades(self._trades)

    def list_assets(self, active_only=True):
        return [a for a in self._assets if a.is_active or not active_only]


class FakeAssetPriceRepo:
    def __init__(self):
        self.latest: Dict[int, AssetLatestPrice] = {}
        self.daily: List[AssetPrice] = []

    def get_latest_prices(self, ids):
        return {i: self.latest[i] for i in ids if i in self.latest}

    def get_last_daily_price(self, asset_id, on_or_before=None):
        rows = [p for p in self.daily if p.asset_id == asset_id and (on_or_before is None or p.price_date <= on_or_before)]
        return max(rows, key=lambda p: p.price_date) if rows else None


class FakeFx:
    def __init__(self, rates: Dict[str, str]):
        self._rates = {k: D(v) for k, v in rates.items()}

    def get_rate(self, base, quote, on_date=None):
        if base == quote:
            return D("1")
        return self._rates.get(f"{base}{quote}")

    def get_rate_dated(self, base, quote):
        rate = self.get_rate(base, quote)
        return None if rate is None else (rate, self.rate_date)

    rate_date = DAY


# ---------------- kurulum yardımcıları ---------------- #


def bist_trade(stock_id, qty, price, day=date(2026, 1, 2)):
    return Trade(None, stock_id, day, None, TradeSide.BUY, qty, D(price))


def asset_trade(asset_id, qty, price, fx, **options):
    day, side = options.get("day", date(2026, 1, 2)), options.get("side", TradeSide.BUY)
    return AssetTrade(None, asset_id, day, None, side, D(qty), D(price), D(fx))


BTC = Asset(1, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD")
AAPL = Asset(2, "AAPL", "Apple", AssetClass.US_STOCK, "USD", "AAPL")
GOLD_G = Asset(3, "XAU", "Altın (gram)", AssetClass.PRECIOUS_METAL, "USD", "GC=F", AssetUnit.GRAM)


def latest(asset_id, price, as_of=NOON):
    return AssetLatestPrice(None, asset_id, D(price), "USD", as_of, "yfinance", as_of)


def daily(asset_id, day, close):
    return AssetPrice(None, asset_id, day, D(close), "USD", "yfinance")


def build(**options):
    """Seçenekler: bist_trades, cash, bist_prices, bist_changes, assets, asset_trades, fx, price_repo."""
    bist_trades, cash = options.get("bist_trades", ()), options.get("cash", "0")
    bist_prices, bist_changes = options.get("bist_prices"), options.get("bist_changes")
    assets, asset_trades = options.get("assets", ()), options.get("asset_trades", ())
    fx, price_repo = options.get("fx"), options.get("price_repo")
    stocks = [Stock(1, "THYAO.IS", "Türk Hava Yolları"), Stock(2, "GARAN", "Garanti")]
    bist = BistHoldingsReader(
        FakePortfolioService(list(bist_trades), cash), FakeStockLookup(stocks), FakeResolver(bist_prices or {}, bist_changes)
    )
    repo = price_repo or FakeAssetPriceRepo()
    fx_service = options.get("fx_service") or FakeFx(fx if fx is not None else {"USDTRY": "40"})
    asset_reader = AssetHoldingsReader(
        FakeLedgerService(list(assets), list(asset_trades)), repo, fx_service, today=options.get("today", lambda: DAY)
    )
    return UnifiedPortfolioService(bist, asset_reader, fx_service), repo


# ---------------- testler ---------------- #


class TestBistOnly:
    def test_values_bist_positions_cash_and_strips_suffix(self):
        service, _ = build(
            bist_trades=[bist_trade(1, 10, "100"), bist_trade(2, 5, "200")], cash="500",
            bist_prices={1: "120", 2: "190"},
        )

        result = service.get_summary()

        assert [h.symbol for h in result.holdings] == ["THYAO", "GARAN"]   # değere göre azalan: 1200 > 950
        thy = result.holdings[0]
        assert (thy.value_try, thy.cost_try, thy.unrealized_pl_try) == (D("1200"), D("1000"), D("200"))
        assert thy.allocation_class == AllocationClass.BIST_STOCK and thy.name == "Türk Hava Yolları"
        assert result.cash_try == D("500")
        assert result.total_value_try == D("2650")
        assert result.total_cost_try == D("2000")
        assert result.unrealized_pl_try == D("150")
        assert not result.is_partial

    def test_daily_gain_comes_from_resolver_change(self):
        service, _ = build(bist_trades=[bist_trade(1, 10, "100")], bist_prices={1: "110"}, bist_changes={1: "10"})

        result = service.get_summary()

        assert result.daily_gain_try == D("100")      # 10 lot: 1100 - 1000
        assert result.daily_change_pct == D("10")

    def test_position_without_price_is_valued_at_cost_and_flagged(self):
        service, _ = build(bist_trades=[bist_trade(1, 10, "100")], bist_prices={})

        result = service.get_summary()

        only = result.holdings[0]
        assert only.value_try == D("1000") and not only.is_priced
        assert result.is_partial and result.unpriced_symbols == ("THYAO",)


class TestAssetValuation:
    def test_foreign_asset_uses_current_fx_and_keeps_historical_cost(self):
        repo = FakeAssetPriceRepo()
        repo.latest[1] = latest(1, "70000")
        service, _ = build(assets=[BTC], asset_trades=[asset_trade(1, "0.5", "60000", "30")], fx={"USDTRY": "40"}, price_repo=repo)

        holding = service.get_summary().holdings[0]

        assert holding.allocation_class == AllocationClass.CRYPTO
        assert (holding.price_native, holding.value_native) == (D("70000"), D("35000"))
        assert holding.value_try == D("1400000")
        assert holding.cost_try == D("900000") and holding.cost_native == D("30000")
        assert holding.unrealized_pl_try == D("500000")        # kur farkı dahil

    def test_gram_gold_converts_ounce_quote_to_gram_price(self):
        repo = FakeAssetPriceRepo()
        repo.latest[3] = latest(3, str(TROY_OUNCE_GRAMS * 100))   # 100 USD/gram
        service, _ = build(assets=[GOLD_G], asset_trades=[asset_trade(3, "10", "80", "30")], fx={"USDTRY": "40"}, price_repo=repo)

        holding = service.get_summary().holdings[0]

        assert holding.price_native == D("100")
        assert holding.value_native == D("1000")
        assert holding.value_try == D("40000")

    def test_gram_gold_traded_in_try_is_valued_in_try_per_gram(self):
        gold_try = Asset(3, "XAU", "Altın (gram)", AssetClass.PRECIOUS_METAL, "USD", "GC=F", AssetUnit.GRAM, trade_currency="TRY")
        repo = FakeAssetPriceRepo()
        repo.latest[3] = latest(3, str(TROY_OUNCE_GRAMS * 100))   # 100 USD/gram, kur 40 -> 4.000 TL/gram
        service, _ = build(assets=[gold_try], asset_trades=[asset_trade(3, "10", "3000", "1")], fx={"USDTRY": "40"}, price_repo=repo)

        holding = service.get_summary().holdings[0]

        # alım 10 g x 3.000 TL = 30.000 TL; şimdi 10 g x 4.000 TL = 40.000 TL
        assert holding.native_currency == "TRY" and holding.price_native == D("4000")
        assert (holding.value_native, holding.value_try) == (D("40000"), D("40000"))
        assert (holding.cost_native, holding.cost_try, holding.unrealized_pl_try) == (D("30000"), D("30000"), D("10000"))

    def test_newer_daily_close_wins_over_stale_latest(self):
        repo = FakeAssetPriceRepo()
        repo.latest[1] = latest(1, "100", datetime(2026, 1, 2, 10, 0))
        repo.daily.append(daily(1, date(2026, 1, 5), "130"))
        service, _ = build(assets=[BTC], asset_trades=[asset_trade(1, "1", "100", "40")], price_repo=repo)

        assert service.get_summary().holdings[0].price_native == D("130")

    def test_latest_wins_on_same_day(self):
        repo = FakeAssetPriceRepo()
        repo.latest[1] = latest(1, "135")
        repo.daily.append(daily(1, DAY, "130"))
        service, _ = build(assets=[BTC], asset_trades=[asset_trade(1, "1", "100", "40")], price_repo=repo)

        assert service.get_summary().holdings[0].price_native == D("135")

    def test_daily_change_is_measured_against_previous_close(self):
        repo = FakeAssetPriceRepo()
        repo.latest[1] = latest(1, "110")
        repo.daily += [daily(1, date(2026, 1, 2), "100"), daily(1, DAY, "108")]   # bugünün kapanışı önceki sayılmaz
        service, _ = build(assets=[BTC], asset_trades=[asset_trade(1, "1", "100", "40")], fx={"USDTRY": "40"}, price_repo=repo)

        result = service.get_summary()

        assert result.holdings[0].daily_change_pct == D("10")
        assert result.daily_gain_try == D("4400") - D("4400") / D("1.1")

    def test_no_price_falls_back_to_cost_and_marks_partial(self):
        service, _ = build(assets=[BTC], asset_trades=[asset_trade(1, "1", "100", "30")])

        result = service.get_summary()

        assert result.holdings[0].value_try == D("3000") and not result.holdings[0].is_priced
        assert result.unpriced_symbols == ("BTC",) and result.is_partial

    def test_missing_fx_rate_marks_partial_even_with_price(self):
        repo = FakeAssetPriceRepo()
        repo.latest[1] = latest(1, "70000")
        service, _ = build(assets=[BTC], asset_trades=[asset_trade(1, "1", "60000", "30")], fx={}, price_repo=repo)

        result = service.get_summary()

        assert result.holdings[0].value_try == D("1800000") and result.is_partial

    def test_closed_positions_and_unknown_assets_are_ignored(self):
        trades = [
            asset_trade(1, "1", "100", "30"), asset_trade(1, "1", "110", "30", day=date(2026, 1, 3), side=TradeSide.SELL),
            asset_trade(9, "1", "100", "30"),   # tanımı olmayan varlık
        ]
        service, _ = build(assets=[BTC], asset_trades=trades)

        assert service.get_summary().holdings == ()


class TestAllocation:
    @pytest.fixture
    def mixed(self):
        repo = FakeAssetPriceRepo()
        repo.latest[1] = latest(1, "100")
        repo.latest[2] = latest(2, "50")
        return build(
            bist_trades=[bist_trade(1, 10, "100")], cash="1000", bist_prices={1: "100"},
            assets=[BTC, AAPL], asset_trades=[asset_trade(1, "1", "90", "40"), asset_trade(2, "10", "45", "40")],
            fx={"USDTRY": "40"}, price_repo=repo,
        )[0]

    def test_slices_group_by_class_with_cash_and_sorted_by_value(self, mixed):
        result = mixed.get_summary()

        values = {s.allocation_class: s.value_try for s in result.slices}
        assert values == {
            AllocationClass.US_STOCK: D("20000"),
            AllocationClass.CRYPTO: D("4000"),
            AllocationClass.BIST_STOCK: D("1000"),
            AllocationClass.CASH: D("1000"),
        }
        assert [s.allocation_class for s in result.slices][0] == AllocationClass.US_STOCK
        assert sum(s.weight_pct for s in result.slices) == D("100")
        assert {s.allocation_class: s.holdings_count for s in result.slices}[AllocationClass.CASH] == 0

    def test_holding_weights_sum_with_cash_to_total(self, mixed):
        result = mixed.get_summary()

        weights = sum(h.weight_pct for h in result.holdings)
        cash_weight = result.cash_try / result.total_value_try * 100
        assert weights + cash_weight == D("100")
        assert result.total_value_try == D("26000")

    def test_holdings_of_filters_by_class(self, mixed):
        result = mixed.get_summary()

        assert [h.symbol for h in result.holdings_of(AllocationClass.US_STOCK)] == ["AAPL"]

    def test_empty_portfolio(self):
        result = build()[0].get_summary()

        assert result.holdings == () and result.slices == ()
        assert result.total_value_try == D("0") and result.unrealized_pl_pct is None


class TestDisplayCurrency:
    def test_try_is_default(self):
        result = build(cash="100")[0].get_summary()

        assert (result.display_currency, result.display_rate, result.display_unavailable) == ("TRY", D("1"), False)

    def test_usd_divides_by_current_usd_try_rate(self):
        result = build(cash="400", fx={"USDTRY": "40"})[0].get_summary("usd")

        assert result.display_currency == "USD"
        assert result.usd_try_rate == D("40")
        assert result.display_amount(result.total_value_try) == D("10")

    def test_usd_falls_back_to_try_when_rate_missing(self):
        result = build(cash="400", fx={})[0].get_summary("USD")

        assert (result.display_currency, result.display_unavailable) == ("TRY", True)
        assert result.display_amount(D("400")) == D("400")

    def test_unsupported_currency_is_rejected(self):
        with pytest.raises(ValueError, match="Desteklenmeyen"):
            build()[0].get_summary("EUR")


class TestStaleness:
    def test_fresh_price_and_fx_are_not_stale(self):
        service, repo = build(assets=[BTC], asset_trades=[asset_trade(1, "1", "100", "30")])
        repo.latest[1] = latest(1, "120")
        summary = service.get_summary()
        assert summary.stale_symbols == () and not summary.holdings[0].is_stale

    def test_old_price_marks_holding_stale_but_keeps_value(self):
        service, repo = build(
            assets=[BTC], asset_trades=[asset_trade(1, "1", "100", "30")], today=lambda: date(2026, 1, 20)
        )
        repo.latest[1] = latest(1, "120")
        summary = service.get_summary()
        assert summary.stale_symbols == ("BTC",) and summary.holdings[0].is_priced
        assert summary.holdings[0].value_try == D("120") * D("40")

    def test_old_fx_marks_foreign_asset_stale(self):
        fx = FakeFx({"USDTRY": "40"})
        fx.rate_date = date(2025, 12, 1)
        service, repo = build(assets=[AAPL], asset_trades=[asset_trade(2, "1", "100", "30")], fx_service=fx)
        repo.latest[2] = latest(2, "120")
        assert service.get_summary().stale_symbols == ("AAPL",)
