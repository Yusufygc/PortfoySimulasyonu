"""
MarketAdjustmentController — Tüm BIST için sermaye artırımı/bölünme fiyat düzeltmesi paneli (QML).

Ayarlar > Piyasa Düzeltmeleri sekmesini besler:
- Veri güdümlü tarama (DuckDB ham seride büyük günlük kırılmalar) ile aday olayları bulma
- Adayı (faktörü düzenleyerek) onaylama, reddetme, geri alma
- Onaylı olaylar tüm BIST taramalarında/grafiklerde düzeltilmiş fiyat olarak kullanılır; ham barlar değişmez
Ağır işler (tarama) arka planda çalışır, sonuçlar Qt sinyalleriyle ana thread'e taşınır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.market_corporate_action import MarketActionStatus, MarketCorporateAction
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import tr_number

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    MarketActionStatus.CANDIDATE: "Onay bekliyor",
    MarketActionStatus.CONFIRMED: msg("market_adjustment.onayli_uygulaniyor"),
    MarketActionStatus.IGNORED: "Reddedildi",
    MarketActionStatus.NO_BREAK: msg("market_adjustment.ham_veride_kirilma_yok"),
}
_MAX_ROWS = 400


def _fmt_factor(value: float) -> str:
    return f"{value:.4f}".replace(".", ",")


def _parse_factor(text: str) -> Optional[float]:
    try:
        value = float(str(text).strip().replace(",", "."))
    except ValueError:
        return None
    return value if value > 0 else None


def _parse_iso(text: str) -> Optional[date]:
    try:
        return datetime.strptime((text or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


class MarketAdjustmentController(QObject):
    """QML context property: marketAdjustmentController"""

    actionsChanged = Signal()
    busyChanged = Signal()
    notification = Signal(bool, str, arguments=["success", "message"])
    # Onay/red sonrası fiyat serileri değişti: tarama/grafik ekranları yeniden okunmalı
    adjustmentsChanged = Signal()

    _scanFinished = Signal(object, str)

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._actions: List[Dict[str, Any]] = []
        self._total = 0
        self._is_busy = False
        self._scanFinished.connect(self._on_scan_finished)

    # ------------------------------------------------------------------ servis

    @property
    def _service(self):
        return getattr(self._container, "market_corporate_action_service", None) if self._container else None

    # ------------------------------------------------------------------ properties

    @Property("QVariantList", notify=actionsChanged)
    def actions(self) -> list:
        return self._actions

    @Property(int, notify=actionsChanged)
    def totalCount(self) -> int:
        return self._total

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(bool, constant=True)
    def serviceAvailable(self) -> bool:
        return self._service is not None

    def _set_busy(self, busy: bool) -> None:
        if self._is_busy != busy:
            self._is_busy = busy
            self.busyChanged.emit()

    # ------------------------------------------------------------------ slots

    @Slot(str, str, int)
    def refresh(self, status: str, ticker_query: str, since_year: int) -> None:
        """Olayları listeler. status boşsa hepsi; since_year > 0 ise o yıldan itibaren; ticker_query alt metin arar."""
        service = self._service
        if service is None:
            self._actions, self._total = [], 0
            self.actionsChanged.emit()
            return
        try:
            wanted = MarketActionStatus(status) if status else None
            rows = service.list_actions(status=wanted)
        except Exception as exc:
            logger.exception("Piyasa düzeltmeleri okunamadı: %s", exc)
            rows = []
        query = (ticker_query or "").strip().upper()
        if query:
            rows = [r for r in rows if query in r.ticker]
        if since_year > 0:
            rows = [r for r in rows if r.effective_date.year >= since_year]
        rows.sort(key=lambda r: (r.status != MarketActionStatus.CANDIDATE, -r.effective_date.toordinal(), r.ticker))
        self._total = len(rows)
        self._actions = [self._to_dict(r) for r in rows[:_MAX_ROWS]]
        self.actionsChanged.emit()

    @Slot()
    def scan(self) -> None:
        service = self._service
        if service is None or self._is_busy:
            return
        self._set_busy(True)

        def work() -> None:
            try:
                self._scanFinished.emit(service.scan(), "")
            except Exception as exc:
                logger.exception("Kurumsal aksiyon taraması başarısız: %s", exc)
                self._scanFinished.emit(None, str(exc))

        self._executor.submit(work)

    @Slot(str, str, str)
    def confirm(self, ticker: str, effective_date: str, factor_text: str) -> None:
        service, when = self._service, _parse_iso(effective_date)
        factor = _parse_factor(factor_text) if factor_text else None
        if service is None or when is None or (factor_text and factor is None):
            self.notification.emit(False, msg("market_adjustment.gecersiz_faktor_veya_tarih"))
            return
        try:
            service.confirm(ticker, when, factor)
        except Exception as exc:
            self.notification.emit(False, msg("market_adjustment.onaylanamadi", exc=exc))
            return
        self.notification.emit(True, msg("market_adjustment.duzeltmesi_onaylandi_fiyat_serileri_duzeltil", ticker=ticker))
        self.adjustmentsChanged.emit()

    @Slot(str, str)
    def ignore(self, ticker: str, effective_date: str) -> None:
        self._set_status(ticker, effective_date, MarketActionStatus.IGNORED, msg("market_adjustment.adayi_reddedildi", ticker=ticker))

    @Slot(str, str)
    def reopen(self, ticker: str, effective_date: str) -> None:
        """Onaylı/reddedilmiş olayı yeniden onay bekliyor durumuna alır (onaylıysa düzeltme geri alınır)."""
        self._set_status(ticker, effective_date, MarketActionStatus.CANDIDATE, msg("market_adjustment.olayi_yeniden_onay_bekliyor", ticker=ticker))

    # ------------------------------------------------------------------ iç işleyiş

    def _set_status(self, ticker: str, effective_date: str, status: MarketActionStatus, message: str) -> None:
        service, when = self._service, _parse_iso(effective_date)
        if service is None or when is None:
            self.notification.emit(False, msg("market_adjustment.gecersiz_olay"))
            return
        try:
            service.set_status(ticker, when, status)
        except Exception as exc:
            self.notification.emit(False, msg("market_adjustment.islem_basarisiz", exc=exc))
            return
        self.notification.emit(True, message)
        self.adjustmentsChanged.emit()

    def _on_scan_finished(self, result: Any, error: str) -> None:
        self._set_busy(False)
        if error:
            self.notification.emit(False, msg("market_adjustment.tarama_basarisiz", error=error))
            return
        count = len(result.new_candidates)
        self.notification.emit(
            True,
            msg("market_adjustment.tarama_bitti_yeni_aday_veri_hatasi", count=count, glitches=result.glitches, already_known=result.already_known),
        )
        self.adjustmentsChanged.emit()

    @staticmethod
    def _to_dict(action: MarketCorporateAction) -> Dict[str, Any]:
        confidence = action.confidence
        return {
            "ticker": action.ticker,
            "dateIso": action.effective_date.isoformat(),
            "dateText": action.effective_date.strftime("%d.%m.%Y"),
            "factor": action.factor,
            "factorText": _fmt_factor(action.factor),
            "observedText": "-" if action.observed_ratio is None else _fmt_factor(action.observed_ratio),
            "confidenceText": "-" if confidence is None else f"%{tr_number(confidence * 100, 0)}",
            "status": action.status.value,
            "statusLabel": STATUS_LABELS[action.status],
            "source": action.source.value,
            "note": action.note,
            "isActive": action.status == MarketActionStatus.CONFIRMED,
            "canConfirm": action.status in (MarketActionStatus.CANDIDATE, MarketActionStatus.IGNORED),
        }
