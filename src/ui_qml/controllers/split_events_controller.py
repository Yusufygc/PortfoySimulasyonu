"""SplitEventsController — Ayarlar > Kurumsal Aksiyonlar: otomatik/uygulanmış hisse bölünmeleri, geri alma, tarama.

QML context property: `splitEventsController`. Servis çağrıları arka plan iş parçacığında çalışır; sonuç ana
iş parçacığına sinyalle döner.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.split_event import SplitEvent, SplitEventStatus
from src.ui_qml.controllers.deps import ServiceView
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number

logger = logging.getLogger(__name__)



def _source_label(source: str) -> str:
    if source == "PRICE_BREAK":
        return msg("split.kaynak_fiyat_kirilmasi")
    return "Yahoo" if source == "YAHOO" else source


def _ledger_label(ledger: str) -> str:
    if ledger == "MODEL":
        return msg("split.defter_model")
    return msg("split.defter_asset") if ledger == "ASSET" else msg("split.defter_main")


def split_event_row(event: SplitEvent) -> Dict[str, Any]:
    """QML satırı: olay ve defter etkisi özeti."""
    ledgers = sorted({c.ledger.value for c in event.trade_changes})
    cash = sum((e.amount for e in event.cash_entries), Decimal("0"))
    return {
        "id": event.id,
        "ticker": event.ticker,
        "ratioText": f"{tr_number(event.multiplier, 4).rstrip('0').rstrip(',')}:1",  # 11:1, 7,3834:1
        "exDateText": event.ex_date.strftime("%d.%m.%Y"),
        "sourcesText": ", ".join(_source_label(s) for s in event.sources.split(",") if s),
        "auto": bool(event.auto_applied),
        "applied": event.status == SplitEventStatus.APPLIED,
        "statusText": msg("split.durum_uygulandi") if event.status == SplitEventStatus.APPLIED else msg("split.durum_geri_alindi"),
        "tradeCount": len(event.trade_changes),
        "ledgersText": ", ".join(_ledger_label(name) for name in ledgers),
        "cashText": f"₺{tr_number(cash)}" if cash else "",
        "pricesText": msg("split.fiyat_duzeltildi", count=event.price_adjustment_count)
        if event.price_adjustment_count else msg("split.fiyat_zaten_tutarli"),
    }


class SplitEventsController(QObject):
    REQUIRES = ("split_automation_service",)
    eventsChanged = Signal()
    busyChanged = Signal()
    autoApplyChanged = Signal()
    notification = Signal(bool, str, arguments=["success", "message"])
    portfolioChanged = Signal()  # bölünme uygulandı/geri alındı: portföy ekranları yenilenmeli

    _finished = Signal(str, object, str)

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._deps = ServiceView(container, self.REQUIRES)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._events: List[Dict[str, Any]] = []
        self._busy = False
        self._finished.connect(self._on_finished)

    @property
    def _service(self):
        return self._deps.split_automation_service

    # ------------------------------------------------------------------ özellikler
    @Property("QVariantList", notify=eventsChanged)
    def events(self) -> list:
        return self._events

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._busy

    @Property(bool, constant=True)
    def available(self) -> bool:
        return self._service is not None

    @Property(bool, notify=autoApplyChanged)
    def autoApply(self) -> bool:
        return bool(self._service and self._service.auto_apply_enabled())

    # ------------------------------------------------------------------ eylemler
    @Slot()
    def refresh(self) -> None:
        if self._service is None:
            return
        try:
            self._events = [split_event_row(e) for e in self._service.list_events()]
        except Exception as exc:
            logger.warning("Bölünme kayıtları okunamadı: %s", exc, exc_info=True)
            self._events = []
        self.eventsChanged.emit()

    @Slot(bool)
    def setAutoApply(self, enabled: bool) -> None:
        if self._service is not None:
            self._service.set_auto_apply(enabled)
            self.autoApplyChanged.emit()

    @Slot()
    def scanNow(self) -> None:
        self._submit("scan", lambda: self._service.run())

    @Slot(int)
    def revert(self, event_id: int) -> None:
        self._submit("revert", lambda: self._service.revert(event_id))

    def _submit(self, job: str, fn) -> None:
        if self._service is None or self._busy:
            return
        self._set_busy(True)

        def work() -> None:
            try:
                self._finished.emit(job, fn(), "")
            except Exception as exc:
                logger.warning("Bölünme işlemi başarısız (%s): %s", job, exc, exc_info=True)
                self._finished.emit(job, None, str(exc))

        self._executor.submit(work)

    def _on_finished(self, job: str, result: Any, error: str) -> None:
        self._set_busy(False)
        if error and job == "revert":
            self.notification.emit(False, msg("split.geri_alma_basarisiz", error=error))
        elif error:
            self.notification.emit(False, msg("split.tarama_basarisiz", error=error))
        elif job == "revert":
            self.notification.emit(True, msg("split.geri_alindi", ticker=result.ticker))
            self.portfolioChanged.emit()
        else:
            self._notify_scan(result)
        self.refresh()

    def _notify_scan(self, result: Any) -> None:
        applied, candidates = result.applied, result.candidates
        if applied:
            self.notification.emit(True, msg("startup.bolunme_otomatik_uygulandi", summary=result.summary))
            self.portfolioChanged.emit()
        elif candidates:
            self.notification.emit(True, msg("startup.bolunme_adayi_onay_bekliyor", count=len(candidates)))
        else:
            self.notification.emit(True, msg("split.yeni_bolunme_yok"))

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit()
