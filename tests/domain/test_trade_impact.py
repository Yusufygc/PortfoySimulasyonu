"""Emir ön izlemesi (`preview_order`): beklenen değerler elle hesaplanmıştır."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.domain.models.trade import TradeSide
from src.domain.models.trade_impact import INSUFFICIENT_CASH, INSUFFICIENT_LOTS, OrderSpec, preview_order

D = Decimal


def test_buy_updates_weighted_average_and_reduces_cash():
    # 10 lot x 100 üzerine 10 lot x 120 al: ortalama 110, nakit 5000 - 1200 = 3800
    impact = preview_order(OrderSpec(TradeSide.BUY, 10, D("120")), 10, D("100"), D("5000"))
    assert (impact.valid, impact.reason) == (True, "")
    assert (impact.new_quantity, impact.new_avg_cost, impact.cash_after) == (20, D("110"), D("3800"))


def test_buy_without_enough_cash_is_invalid():
    impact = preview_order(OrderSpec(TradeSide.BUY, 10, D("120")), 0, D("0"), D("1000"))
    assert not impact.valid and impact.reason == INSUFFICIENT_CASH and impact.cash_after == D("-200")


def test_sell_keeps_average_and_adds_cash_and_oversell_is_invalid():
    sell = preview_order(OrderSpec(TradeSide.SELL, 4, D("130")), 10, D("100"), D("0"))
    assert (sell.valid, sell.new_quantity, sell.new_avg_cost, sell.cash_after) == (True, 6, D("100"), D("520"))

    oversell = preview_order(OrderSpec(TradeSide.SELL, 11, D("130")), 10, D("100"), D("0"))
    assert not oversell.valid and oversell.reason == INSUFFICIENT_LOTS and oversell.new_quantity == -1


def test_unknown_cash_and_empty_order():
    impact = preview_order(OrderSpec(TradeSide.BUY, 5, D("10")), 0, D("0"), None)
    assert impact.valid and impact.cash_after is None and impact.new_avg_cost == D("10")

    empty = preview_order(OrderSpec(TradeSide.BUY, 0, D("10")), 3, D("50"), D("100"))
    assert not empty.valid and empty.reason == ""
    assert not preview_order(OrderSpec(TradeSide.BUY, 5, D("0")), 3, D("50"), D("100")).valid  # fiyat yok
