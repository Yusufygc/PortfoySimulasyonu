"""Türkçe sayı/para/yüzde biçimleyicileri (denetleyicilerdeki eski kopyaların davranışı korunur)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.ui_qml.presenters.formatting import tr_money, tr_number, tr_number_or_dash, tr_pct


@pytest.mark.parametrize(
    "value, decimals, expected",
    [
        (1234.5, 2, "1.234,50"),
        (Decimal("1234567.891"), 2, "1.234.567,89"),
        (Decimal("0.12346"), 4, "0,1235"),
        (-62608.18, 2, "-62.608,18"),
        (0, 2, "0,00"),
    ],
)
def test_tr_number(value, decimals, expected):
    assert tr_number(value, decimals) == expected


def test_tr_money_handles_none_negative_and_unparsable():
    assert tr_money(1234567.891) == "1.234.567,89 ₺"
    assert tr_money(Decimal("1000")) == "1.000,00 ₺"
    assert tr_money(-62608.18) == "-62.608,18 ₺"
    assert tr_money(None) == "0,00 ₺"
    assert tr_money("abc") == "abc ₺"


def test_tr_pct_sign_rules():
    assert tr_pct(16.32) == "%16,32"
    assert tr_pct(-5.82) == "-%5,82"
    assert tr_pct(11.68, with_sign=True) == "+%11,68"
    assert tr_pct(-8.45, with_sign=True) == "-%8,45"
    assert tr_pct(Decimal("1.07"), with_sign=True) == "+%1,07"


@pytest.mark.parametrize("value", [None, 0.0, 0.00001, -0.00001, float("nan"), float("inf")])
def test_tr_pct_zero_like_values(value):
    assert tr_pct(value, with_sign=True) == "%0,00"


def test_tr_number_or_dash():
    assert tr_number_or_dash(None) == "-"
    assert tr_number_or_dash(1234.5) == "1.234,50"
    assert tr_number_or_dash("n/a") == "n/a"
