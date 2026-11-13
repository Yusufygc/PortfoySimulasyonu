from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace as NS

from src.domain.models.split_event import (
    SplitCashEntry,
    SplitEvent,
    SplitEventStatus,
    SplitLedger,
    SplitTradeChange,
)
from src.ui_qml.controllers.split_events_controller import SplitEventsController, split_event_row


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _event(status=SplitEventStatus.APPLIED, cash=()):
    return SplitEvent(
        id=7, ticker="SDTTR", ex_date=date(2026, 8, 21), multiplier=D("11"), sources="PRICE_BREAK,YAHOO",
        auto_applied=True, status=status, stock_id=79, price_adjustment_count=6,
        trade_changes=(SplitTradeChange(SplitLedger.MODEL, 34, D("65"), D("715"), D("242"), D("22"), 9),),
        cash_entries=cash,
    )


class FakeService:
    def __init__(self, events=(), fail=False):
        self.events, self.fail, self.auto = list(events), fail, True
        self.reverted = []

    def list_events(self):
        return self.events

    def auto_apply_enabled(self):
        return self.auto

    def set_auto_apply(self, enabled):
        self.auto = enabled

    def revert(self, event_id):
        if self.fail:
            raise ValueError("işlem değişmiş")
        self.reverted.append(event_id)
        return NS(ticker="SDTTR")

    def run(self):
        return NS(applied=[], candidates=[], summary="")


def _controller(qapp, service):
    ctrl = SplitEventsController(container=NS(split_automation_service=service))
    ctrl._executor = ImmediateExecutor()
    return ctrl


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def test_row_formats_ratio_sources_ledgers_and_cash():
    row = split_event_row(_event(cash=(SplitCashEntry(SplitLedger.MAIN, D("1.95"), date(2026, 8, 21)),)))
    assert row["ratioText"] == "11:1"
    assert row["exDateText"] == "21.08.2026"
    assert row["sourcesText"] == "Fiyat kırılması, Yahoo"
    assert row["ledgersText"] == "Model portföy"
    assert row["cashText"] == "₺1,95"
    assert row["pricesText"] == "6 fiyat kaydı düzeltildi"
    assert row["applied"] and row["auto"]


def test_row_for_fractional_multiplier_and_reverted_event():
    event = SplitEvent(id=1, ticker="MERKO", ex_date=date(2026, 5, 5), multiplier=D("7.3834"), sources="KAP",
                       auto_applied=False, status=SplitEventStatus.REVERTED, stock_id=47)
    row = split_event_row(event)
    assert row["ratioText"] == "7,3834:1" and not row["applied"]
    assert row["statusText"] == "Geri alındı" and row["pricesText"] == "Fiyat geçmişi zaten tutarlıydı"


def test_refresh_and_revert_success(qapp):
    service = FakeService([_event()])
    ctrl = _controller(qapp, service)
    notes, changed = _capture(ctrl.notification), _capture(ctrl.portfolioChanged)
    ctrl.refresh()
    assert [r["id"] for r in ctrl.events] == [7]

    ctrl.revert(7)

    assert service.reverted == [7] and len(changed) == 1
    assert notes[-1][0] is True and "SDTTR bölünmesi geri alındı" in notes[-1][1]
    assert not ctrl.isBusy


def test_revert_failure_is_reported(qapp):
    ctrl = _controller(qapp, FakeService([_event()], fail=True))
    notes, changed = _capture(ctrl.notification), _capture(ctrl.portfolioChanged)
    ctrl.revert(7)
    assert notes == [(False, "Bölünme geri alınamadı: işlem değişmiş")] and changed == []


def test_auto_apply_toggle_and_empty_scan(qapp):
    service = FakeService()
    ctrl = _controller(qapp, service)
    notes = _capture(ctrl.notification)
    ctrl.setAutoApply(False)
    assert ctrl.autoApply is False and service.auto is False
    ctrl.scanNow()
    assert notes == [(True, "Yeni hisse bölünmesi bulunamadı.")]


def test_controller_without_service_is_safe(qapp):
    ctrl = SplitEventsController(container=None)
    ctrl.refresh()
    ctrl.revert(1)
    ctrl.scanNow()
    assert ctrl.available is False and ctrl.events == [] and ctrl.autoApply is False
