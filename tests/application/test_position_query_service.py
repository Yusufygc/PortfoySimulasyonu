"""PositionQueryService: pozisyon rakamlarının tek okuma kaynağı.

Aynı pozisyonun değeri Portföyüm (`UnifiedPortfolioService`), Hisse Detay (`PositionQueryService`) ve Excel geçmişi
(`HistoryPositionBuilder`) yollarında birebir aynıdır; beklenen değerler elle hesaplanmıştır.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.assets.bist_holdings_reader import BistHoldingsReader
from src.application.services.assets.unified_portfolio_service import UnifiedPortfolioService
from src.application.services.portfolio.position_query_service import PositionQueryService
from src.application.services.simulation.history_position_builder import HistoryPositionBuilder
from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade

D = Decimal
DAY = date(2026, 3, 2)

# AAA: 10 lot x 100 (maliyet 1000) şimdi 120 -> 1200 | BBB: 5 lot x 200 (maliyet 1000) şimdi 180 -> 900 | nakit 500
TRADES = [Trade.create_buy(stock_id=1, trade_date=DAY, quantity=10, price=D("100")),
          Trade.create_buy(stock_id=2, trade_date=DAY, quantity=5, price=D("200"))]
PRICES = {1: D("120"), 2: D("180")}
STOCKS = {1: SimpleNamespace(ticker="AAA.IS", name="A Şirketi"), 2: SimpleNamespace(ticker="BBB.IS", name="B Şirketi")}


class _Resolver:
    def __init__(self, prices):
        self.prices = prices

    def resolve(self, ids):
        return {i: SimpleNamespace(price=self.prices[i]) for i in ids if i in self.prices}

    def price_map(self, ids):
        return {i: p for i, p in self.prices.items() if i in ids}

    def daily_change_pct(self, stock_id, resolved):
        return D("2") if stock_id == 1 else D("-1")

    def previous_close(self, stock_id, resolved):
        return D("100")


class _PortfolioService:
    def __init__(self, trades):
        self.portfolio = Portfolio.from_trades(trades)

    def get_cash_balance(self):
        return D("500")

    def get_current_portfolio(self):
        return self.portfolio


class _Lookup:
    def get_stocks(self, ids):
        return {i: STOCKS[i] for i in ids}

    def get_previous_close(self, stock_id):
        return D("100")


@pytest.fixture
def reader():
    return BistHoldingsReader(_PortfolioService(TRADES), _Lookup(), _Resolver(PRICES))


@pytest.fixture
def service(reader):
    return PositionQueryService(reader, None, _Lookup(), _Resolver(PRICES))


def test_main_position_matches_hand_calculation(service):
    positions = service.main_positions()
    a = positions.find(1)

    assert (a.quantity, a.avg_cost, a.market_value, a.unrealized_pl) == (10, D("100"), D("1200"), D("200"))
    assert a.unrealized_pl_pct == D("20") and a.total_change_pct == D("20") and a.daily_change_pct == D("2")
    assert positions.total_value == D("2600") and positions.cash == D("500")  # 1200 + 900 + 500
    assert a.weight_pct == D("1200") / D("2600") * 100
    assert positions.find(99) is None


def test_same_position_value_in_portfolio_page_detail_and_excel_history(reader, service):
    unified = UnifiedPortfolioService(reader, SimpleNamespace(read=lambda: []), None).get_summary()
    holding = next(h for h in unified.holdings if h.symbol == "AAA")
    snapshot = service.main_position(1)

    portfolio = Portfolio.from_trades(TRADES)
    excel = next(p for p in HistoryPositionBuilder().build(
        DAY, portfolio, PRICES, {1: "AAA", 2: "BBB"}, {}).positions if p.ticker == "AAA")

    assert holding.value_try == snapshot.market_value == excel.position_value == D("1200")
    assert holding.unrealized_pl_try == snapshot.unrealized_pl == excel.unrealized_pnl_tl == D("200")
    assert holding.unrealized_pl_pct == snapshot.unrealized_pl_pct == excel.unrealized_pnl_pct * 100
    assert holding.cost_try == snapshot.total_cost == excel.cost_basis == D("1000")


def test_unpriced_position_is_valued_at_cost(service):
    reader = BistHoldingsReader(_PortfolioService(TRADES), _Lookup(), _Resolver({1: D("120")}))
    positions = PositionQueryService(reader, None, _Lookup(), _Resolver({})).main_positions()
    b = positions.find(2)

    assert not b.is_priced and b.market_value == D("1000") and b.unrealized_pl == D("0")
    assert b.total_change_pct is None and b.daily_change_pct is None


class _ModelService:
    def get_positions(self, portfolio_id):
        return {1: 10}

    def get_positions_with_details(self, portfolio_id, price_map):
        price = price_map.get(1)
        return [{"stock_id": 1, "ticker": "AAA.IS", "name": "A", "quantity": 10, "total_cost": D("1000"),
                 "current_price": price, "current_value": price * 10 if price else None}]

    def get_portfolio_summary(self, portfolio_id, price_map):
        positions_value = sum((p * 10 for p in price_map.values()), D("0"))
        return {"remaining_cash": D("300"), "total_value": D("300") + positions_value}


def test_model_position_weight_uses_total_value_including_priced_positions():
    query = PositionQueryService(None, _ModelService(), _Lookup(), _Resolver(PRICES))

    positions = query.model_positions(7)
    a = positions.find(1)

    # toplam = nakit 300 + 10 x 120; ağırlık = 1200 / 1500 (eskiden Hisse Detay yalnızca nakde bölüyordu)
    assert positions.total_value == D("1500") and a.weight_pct == D("80")
    assert a.market_value == D("1200") and a.daily_change_pct == D("20")  # önceki kapanış 100
    assert query.model_position(7, 1).market_value == a.market_value


def test_model_price_map_uses_resolver_then_previous_close_and_survives_errors():
    class Lookup(_Lookup):
        def get_latest_price_map(self, ids):
            return {}

    query = PositionQueryService(None, _ModelService(), Lookup(), _Resolver({}))
    assert query.model_price_map(7) == {1: D("100")}  # çözümleyici yok -> son kapanış

    class Broken:
        def get_positions(self, _):
            raise RuntimeError("db")

    assert PositionQueryService(None, Broken(), None, None).model_price_map(7) == {}


class _QuoteLookup:
    def __init__(self, live=None, prev=None, bars=(), close=None):
        self.live, self.prev, self.bars, self.close = live, prev, list(bars), close

    def get_latest_price_map(self, ids):
        return {ids[0]: self.live} if self.live is not None else {}

    def get_previous_close(self, stock_id):
        return self.prev

    def get_last_market_bars(self, ticker, count):
        return self.bars

    def get_latest_close(self, ticker):
        return self.close


def _bar(close):
    return SimpleNamespace(close_price=D(close))


def test_quote_prefers_resolver():
    quote = PositionQueryService(None, None, _QuoteLookup(), _Resolver(PRICES)).quote("AAA.IS", 1)
    assert (quote.price, quote.daily_change_pct) == (D("120"), D("2"))


def test_quote_falls_back_to_live_cache_then_bars_then_sqlite_close():
    live = PositionQueryService(None, None, _QuoteLookup(live=D("110"), prev=D("100")), None).quote("AAA", 1)
    assert (live.price, live.daily_change_pct) == (D("110"), D("10"))

    bars = PositionQueryService(None, None, _QuoteLookup(bars=[_bar("105"), _bar("100")]), None).quote("AAA", 1)
    assert (bars.price, bars.daily_change_pct) == (D("105"), D("5"))

    sqlite = PositionQueryService(None, None, _QuoteLookup(prev=D("99")), None).quote("AAA", 1)
    assert (sqlite.price, sqlite.daily_change_pct) == (D("99"), D("0"))

    ticker_only = PositionQueryService(None, None, _QuoteLookup(close=D("98")), None).quote("AAA.IS")
    assert ticker_only.price == D("98")

    empty = PositionQueryService(None, None, _QuoteLookup(), None).quote("AAA", 1)
    assert (empty.price, empty.daily_change_pct) == (D("0"), D("0"))
    assert PositionQueryService(None, None, None, None).quote("AAA", 1).price == D("0")
