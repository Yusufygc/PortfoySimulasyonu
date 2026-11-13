"""İşlem ücreti (komisyon + BSMV): alımda maliyete eklenir, satışta gelirden düşer; beklenen değerler elle hesaplanmıştır."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.domain.models.asset_position import AssetPosition
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.position import Position
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.trade_impact import INSUFFICIENT_CASH, OrderSpec, preview_order

D = Decimal
DAY = date(2026, 3, 2)


def test_cash_amount_is_amount_plus_fee_for_buy_and_minus_fee_for_sell():
    buy = Trade.create_buy(1, DAY, 10, D("100"), fee=D("5"))
    sell = Trade.create_sell(1, DAY, 10, D("100"), fee=D("5"))
    assert (buy.total_amount, buy.cash_amount) == (D("1000"), D("1005"))
    assert (sell.total_amount, sell.cash_amount) == (D("1000"), D("995"))
    assert Trade.create_buy(1, DAY, 1, D("1")).fee == D("0")  # varsayılan ücret yok
    with pytest.raises(ValueError):
        Trade.create_buy(1, DAY, 1, D("1"), fee=D("-1"))


def test_position_cost_includes_buy_fee_and_realized_pl_is_net_of_sell_fee():
    position = Position.from_trades(1, [
        Trade.create_buy(1, DAY, 10, D("100"), fee=D("5")),     # maliyet 1005, ortalama 100,5
        Trade.create_sell(1, DAY, 4, D("120"), fee=D("3")),     # gelir 480 - 3 = 477, satılan maliyet 402
    ])
    assert position.average_cost == D("100.5")
    assert position.realized_pl == D("75")                       # 477 - 402
    assert (position.total_quantity, position.total_cost) == (6, D("603"))


def test_preview_includes_fee_in_average_cost():
    quantity, average = Position(stock_id=1, total_quantity=10, total_cost=D("1000")).preview_trade(
        TradeSide.BUY, 10, D("120"), fee=D("20"))
    assert (quantity, average) == (20, D("111"))  # (1000 + 1200 + 20) / 20


def test_asset_position_cost_and_realized_pl_with_fee_and_fx():
    position = AssetPosition.from_trades(3, [
        AssetTrade(None, 3, DAY, None, TradeSide.BUY, D("2"), D("100"), fx_rate_to_try=D("30"), fee=D("1")),
        AssetTrade(None, 3, DAY, None, TradeSide.SELL, D("1"), D("150"), fx_rate_to_try=D("32"), fee=D("0.5")),
    ])
    # alım maliyeti 201 USD (6030 TL); satış neti 149,5 USD (4784 TL); satılan maliyet 100,5 USD (3015 TL)
    assert position.realized_pl == D("49")
    assert position.realized_pl_try == D("4784") - D("3015")
    assert (position.total_cost, position.total_cost_try) == (D("100.5"), D("3015"))


def test_asset_trade_rejects_negative_fee():
    with pytest.raises(ValueError):
        AssetTrade(None, 1, DAY, None, TradeSide.BUY, D("1"), D("1"), fee=D("-0.1"))


def test_preview_order_cash_check_uses_fee():
    # 10 x 100 = 1000 + ücret 5 = 1005 gerekir; nakit 1004 yetmez, 1005 yeter
    short = preview_order(OrderSpec(TradeSide.BUY, 10, D("100"), D("5")), 0, D("0"), D("1004"))
    assert not short.valid and short.reason == INSUFFICIENT_CASH and short.cash_after == D("-1")
    enough = preview_order(OrderSpec(TradeSide.BUY, 10, D("100"), D("5")), 0, D("0"), D("1005"))
    assert enough.valid and enough.cash_after == D("0") and enough.new_avg_cost == D("100.5")
    sell = preview_order(OrderSpec(TradeSide.SELL, 10, D("100"), D("5")), 10, D("90"), D("0"))
    assert sell.cash_after == D("995")
