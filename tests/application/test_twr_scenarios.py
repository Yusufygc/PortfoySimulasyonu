"""Zaman ağırlıklı getiri (TWR) senaryoları: beklenen değerler elle hesaplanmıştır.

TWR dış sermaye akışından (yatırma/çekme) etkilenmez; temettü getiridir. Gün sonu değeri = nakit + lot x kapanış.
Akış günün başında kabul edilir: taban = önceki gün değeri + o günün net akışı.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.portfolio_series_builder import PortfolioSeriesBuilder, PortfolioSeriesRequest
from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade

D = Decimal
MON = date(2026, 3, 2)
DAYS = [MON + timedelta(days=i) for i in range(5)]  # Pazartesi-Cuma


def _run(trades, movements, closes):
    """closes: gün -> kapanış (tek hisse, kimlik 1)."""
    price_repo = MagicMock()
    price_repo.get_price_series.return_value = [SimpleNamespace(price_date=d, close_price=D(c)) for d, c in closes.items()]
    price_repo.get_last_price_before.return_value = None
    request = PortfolioSeriesRequest(
        trades=trades, cash_movements=movements, stock_ids=[1], ticker_map={1: "AAA"},
        start_date=min(closes), end_date=max(closes), portfolio=Portfolio.from_trades(trades),
    )
    values, twr, _, warnings = PortfolioSeriesBuilder(price_repo, MagicMock()).compute_portfolio_series(request)
    assert warnings == []
    return values, twr


def _cash(kind, amount, day, movement_id, stock_id=None):
    return CashMovement(
        id=movement_id, movement_date=day, movement_time=None, type=kind, amount=D(amount), stock_id=stock_id,
    )


def _buy(qty, price, day):
    return Trade.create_buy(stock_id=1, trade_date=day, quantity=qty, price=D(price))


def _sell(qty, price, day):
    return Trade.create_sell(stock_id=1, trade_date=day, quantity=qty, price=D(price))


def test_first_day_return_from_purchase_price_to_close_is_counted():
    # 1000 TL yatır, 10 lot x 100 al; kapanış 110 -> ilk gün %10
    values, twr = _run([_buy(10, "100", DAYS[0])], [_cash(CashMovementType.DEPOSIT, "1000", DAYS[0], 1)],
                       {DAYS[0]: "110", DAYS[1]: "121"})
    assert values[DAYS[0]] == D("1100") and twr[DAYS[0]] == D("110")
    assert twr[DAYS[1]] == D("121")  # 110 x 1,10


def test_deposit_and_withdrawal_do_not_change_twr():
    trades = [_buy(10, "100", DAYS[0])]
    movements = [
        _cash(CashMovementType.DEPOSIT, "1000", DAYS[0], 1),
        _cash(CashMovementType.DEPOSIT, "5000", DAYS[2], 2),   # fiyat değişmezken büyük yatırma
        _cash(CashMovementType.WITHDRAW, "3000", DAYS[3], 3),  # çekme
    ]
    values, twr = _run(trades, movements, {DAYS[0]: "100", DAYS[1]: "120", DAYS[2]: "120", DAYS[3]: "120"})
    assert values[DAYS[3]] == D("3200")  # 10 x 120 + 1000 + 5000 - 1000 - 3000
    assert twr[DAYS[1]] == twr[DAYS[2]] == twr[DAYS[3]] == D("120")


def test_return_on_mixed_cash_and_stock_is_weighted():
    # 2000 TL yatır, yarısıyla al (10 x 100); hisse %20 artınca portföy %10 artar
    values, twr = _run([_buy(10, "100", DAYS[0])], [_cash(CashMovementType.DEPOSIT, "2000", DAYS[0], 1)],
                       {DAYS[0]: "100", DAYS[1]: "120"})
    assert values[DAYS[1]] == D("2200") and twr[DAYS[1]] == D("110")


def test_sell_moves_value_into_cash_without_return_effect():
    trades = [_buy(10, "100", DAYS[0]), _sell(10, "150", DAYS[1])]
    values, twr = _run(trades, [_cash(CashMovementType.DEPOSIT, "1000", DAYS[0], 1)],
                       {DAYS[0]: "100", DAYS[1]: "150", DAYS[2]: "300"})
    assert values[DAYS[1]] == values[DAYS[2]] == D("1500")  # satıştan sonra hisse fiyatı etkilemez
    assert twr[DAYS[1]] == twr[DAYS[2]] == D("150")


def test_dividend_is_return_not_external_flow():
    trades = [_buy(10, "100", DAYS[0])]
    movements = [_cash(CashMovementType.DEPOSIT, "1000", DAYS[0], 1),
                 _cash(CashMovementType.DIVIDEND, "50", DAYS[1], 2, stock_id=1)]
    _, twr = _run(trades, movements, {DAYS[0]: "100", DAYS[1]: "100"})
    assert twr[DAYS[1]] == D("105")


def test_without_cash_tracking_buys_are_inflows():
    # Nakit hareketi yok: alımlar dış akış sayılır. Akış gün başında kabul edildiğinden (taban = önceki değer +
    # akış) 2. gün alınan 1100 TL'lik lot o günün getirisini sulandırır: 2200 / (1000 + 1100) = 1,0476.
    # Bu yöntemin bilinen yaklaşımıdır (gün içi alım saati bilinmez); 3. gün tam %10 sayılır.
    trades = [_buy(10, "100", DAYS[0]), _buy(10, "110", DAYS[1])]
    values, twr = _run(trades, [], {DAYS[0]: "100", DAYS[1]: "110", DAYS[2]: "121"})
    assert values[DAYS[2]] == D("2420")
    assert twr[DAYS[1]] == pytest.approx(D("100") * D("2200") / D("2100"))
    assert twr[DAYS[2]] == pytest.approx(twr[DAYS[1]] * D("1.1"))
