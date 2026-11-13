from datetime import date
from decimal import Decimal as D

import pytest

from src.domain.models.split_signal import SplitDecisionKind, SplitSignal, SplitSource
from src.domain.split_consensus import match_signals
from src.domain.split_math import LedgerLot, allocate_split


def _lot(trade_id, day, is_buy, qty, price):
    return LedgerLot(trade_id, day, None, is_buy, D(qty), D(price))


# ----------------------------------------------------------------- uzlaşı


def test_two_sources_agreeing_within_window_is_auto():
    signals = [
        SplitSignal("SDTTR.IS", date(2026, 8, 27), D("11"), SplitSource.YAHOO),
        SplitSignal("SDTTR", date(2026, 8, 21), D("10.95"), SplitSource.PRICE_BREAK),
    ]
    [decision] = match_signals(signals)
    assert decision.kind == SplitDecisionKind.AUTO
    assert decision.ticker == "SDTTR"
    assert decision.multiplier == D("11")          # medyan öncelikli kaynakla %2 içinde
    assert decision.ex_date == date(2026, 8, 21)    # KAP yoksa fiyat kırılması günü (Yahoo 6 gün geç)
    assert decision.sources == (SplitSource.PRICE_BREAK, SplitSource.YAHOO)
    assert decision.bedelsiz_ratio == D("10")


def test_kap_date_wins_over_yahoo():
    signals = [
        SplitSignal("ABC", date(2026, 8, 27), D("2"), SplitSource.YAHOO),
        SplitSignal("ABC", date(2026, 8, 24), D("2"), SplitSource.KAP),
    ]
    [decision] = match_signals(signals)
    assert decision.ex_date == date(2026, 8, 24)


def test_single_source_is_candidate():
    [decision] = match_signals([SplitSignal("ABC", date(2026, 1, 5), D("2"), SplitSource.YAHOO)])
    assert decision.kind == SplitDecisionKind.CANDIDATE


def test_same_source_twice_is_not_two_sources():
    signals = [
        SplitSignal("ABC", date(2026, 1, 5), D("2"), SplitSource.PRICE_BREAK),
        SplitSignal("ABC", date(2026, 1, 6), D("2"), SplitSource.PRICE_BREAK),
    ]
    [decision] = match_signals(signals)
    assert decision.kind == SplitDecisionKind.CANDIDATE


def test_ratio_or_date_mismatch_splits_into_separate_events():
    signals = [
        SplitSignal("ABC", date(2026, 1, 5), D("2"), SplitSource.YAHOO),
        SplitSignal("ABC", date(2026, 1, 5), D("2.1"), SplitSource.KAP),        # %5 fark
        SplitSignal("ABC", date(2026, 1, 13), D("2"), SplitSource.PRICE_BREAK),  # 8 gün sonra
    ]
    decisions = match_signals(signals)
    assert len(decisions) == 3
    assert all(d.kind == SplitDecisionKind.CANDIDATE for d in decisions)


def test_reverse_split_is_never_auto():
    signals = [
        SplitSignal("ABC", date(2026, 1, 5), D("0.1"), SplitSource.YAHOO),
        SplitSignal("ABC", date(2026, 1, 5), D("0.1"), SplitSource.PRICE_BREAK),
    ]
    [decision] = match_signals(signals)
    assert decision.kind == SplitDecisionKind.CANDIDATE


def test_already_applied_event_is_marked():
    signals = [
        SplitSignal("MERKO", date(2026, 5, 5), D("7.3834"), SplitSource.YAHOO),
        SplitSignal("MERKO", date(2026, 5, 1), D("7.38"), SplitSource.PRICE_BREAK),
    ]
    [decision] = match_signals(signals, applied=[("MERKO.IS", date(2026, 5, 5), D("7.3834"))])
    assert decision.kind == SplitDecisionKind.ALREADY_APPLIED


def test_signal_rejects_neutral_multiplier():
    with pytest.raises(ValueError):
        SplitSignal("ABC", date(2026, 1, 5), D("1"), SplitSource.YAHOO)


# ----------------------------------------------------------------- lot ve küsurat


def test_sdttr_model_trade_11_for_1():
    allocation = allocate_split([_lot(34, date(2026, 8, 7), True, 65, 242)], date(2026, 8, 21), D("11"))
    [adj] = allocation.adjustments
    assert (adj.post_quantity, adj.post_price) == (D("715"), D("22.0000"))
    assert allocation.held_after == D("715")
    assert allocation.fraction == D("0")


def test_bedelsiz_fraction_rounds_down_and_is_paid_in_cash():
    # %638,34 bedelsiz: çarpan 7,3834; 65 lot -> 479,921 -> 479 lot + 0,921 lot küsurat
    allocation = allocate_split([_lot(1, date(2026, 4, 1), True, 65, "15.60")], date(2026, 5, 5), D("7.3834"))
    assert allocation.held_after == D("479")
    assert allocation.fraction == D("0.9210")
    # 0,921 * 15,60 / 7,3834 = 1,9459 -> 1,95 TL
    assert allocation.fraction_cash(D("15.60"), D("7.3834")) == D("1.95")
    # işlem tutarı korunur: 65 * 15,60 = 1014 = 479 * 2,1169 (yuvarlama payıyla)
    assert allocation.adjustments[0].post_price == D("2.1169")


def test_running_floor_keeps_sells_within_holdings():
    lots = [
        _lot(1, date(2026, 1, 2), True, 1, 10),
        _lot(2, date(2026, 1, 3), True, 1, 10),
        _lot(3, date(2026, 1, 4), False, 2, 12),
    ]
    allocation = allocate_split(lots, date(2026, 2, 1), D("1.5"))
    assert [a.post_quantity for a in allocation.adjustments] == [D("1"), D("2"), D("3")]
    assert [a.post_price for a in allocation.adjustments] == [D("10.0000"), D("5.0000"), D("8.0000")]
    assert allocation.held_after == D("0")


def test_trades_on_or_after_ex_date_are_untouched():
    lots = [_lot(1, date(2026, 1, 2), True, 10, 100), _lot(2, date(2026, 2, 1), True, 5, 50)]
    allocation = allocate_split(lots, date(2026, 2, 1), D("2"))
    assert [a.trade_id for a in allocation.adjustments] == [1]
    assert allocation.held_after == D("20")


def test_fractional_ledger_has_no_fraction():
    allocation = allocate_split([_lot(1, date(2026, 1, 2), True, "3.5", 100)], date(2026, 2, 1), D("1.5"), whole_lots=False)
    assert allocation.held_after == D("5.25")
    assert allocation.fraction == D("0")


def test_reverse_split_dropping_trade_to_zero_raises():
    with pytest.raises(ValueError):
        allocate_split([_lot(1, date(2026, 1, 2), True, 5, 1)], date(2026, 2, 1), D("0.1"))
