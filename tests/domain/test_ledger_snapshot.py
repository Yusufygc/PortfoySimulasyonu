from datetime import date
from decimal import Decimal as D

from src.domain.models.ledger import LedgerKind, LedgerSnapshot
from src.domain.split_math import LedgerLot


def _lot(tid, day, buy, qty, inst):
    return LedgerLot(tid, date(2026, 1, day), None, buy, D(qty), D("10"), inst)


SNAP = LedgerSnapshot({
    (LedgerKind.MAIN, None): [_lot(1, 2, True, 10, 7), _lot(2, 5, False, 10, 7), _lot(3, 3, True, 5, 8)],
    (LedgerKind.MODEL, 9): [_lot(4, 4, True, 3, 7), _lot(5, 6, False, 99, 9)],  # 9: eldekinden fazla satış
    (LedgerKind.ASSET, None): [_lot(6, 1, True, "0.5", 3)],
})


def test_instruments_and_open_positions_per_ledger():
    assert SNAP.instruments() == {7, 8, 9, 3}
    # 7 ana portföyde kapandı ama model portföyde açık; 9 için geçersiz satış atlanır (açık değil)
    assert SNAP.open_instruments() == {7, 8, 3}
    assert SNAP.open_instruments(lambda k: k[0] == LedgerKind.MAIN) == {8}


def test_first_trade_dates_and_key_filter():
    assert SNAP.first_trade_dates() == {7: date(2026, 1, 2), 8: date(2026, 1, 3), 9: date(2026, 1, 6), 3: date(2026, 1, 1)}
    assert SNAP.first_trade_dates(lambda k: k == (LedgerKind.MODEL, 9)) == {7: date(2026, 1, 4), 9: date(2026, 1, 6)}
    assert not SNAP.is_empty() and LedgerSnapshot({}).is_empty()
