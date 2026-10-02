"""
GoldenCrossController — Golden / Death Cross (EMA50/EMA200) sinyal taraması QML controller'ı.

Hisse Tarayıcı ekranının "Golden Cross" sekmesini besler:
- Son sinyallerin dönem ve tip filtresiyle listelenmesi
- Tüm BIST için kesişim taraması (TechnicalAnalysisService.scan_all)
- Eksik fiyat verisini tamamlama ve TradingView'den geçmiş veri yükleme
- Tek hissenin kesişim geçmişi
Ağır işler arka plan thread'inde çalışır, sonuçlar Qt sinyalleriyle ana thread'e taşınır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.golden_cross_event import CrossType

logger = logging.getLogger(__name__)

# (etiket, gün sayısı) — 0 = tümü
PERIOD_OPTIONS = [("7 gün", 7), ("30 gün", 30), ("90 gün", 90), ("180 gün", 180), ("1 yıl", 365), ("Tümü", 0)]
TYPE_OPTIONS = [("Hepsi", ""), ("Golden", "GOLDEN"), ("Death", "DEATH")]
_ALL_DAYS = 365 * 20
_TV_BACKFILL_YEARS = 10


def _fmt(value) -> str:
    if value is None:
        return "-"
    try:
        text = f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _clean_ticker(ticker: str) -> str:
    return (ticker or "").replace(".IS", "").strip().upper()


class GoldenCrossController(QObject):
    """QML context property: goldenCrossController"""

    eventsChanged = Signal()
    tickerEventsChanged = Signal()
    busyChanged = Signal()
    statusChanged = Signal()
    # Kesişim taraması bitti; liste mevcut filtreyle yeniden okunmalı
    scanCompleted = Signal()
    # Hisse Tarayıcı toast'ı için
    notification = Signal(bool, str, arguments=["success", "message"])
    # Yeni fiyat yazıldı (veri tamamlama / TV yükleme); fiyata bağlı ekranlar yenilenmeli
    pricesUpdated = Signal()

    # Worker -> ana thread köprüsü: (iş adı, sonuç, hata metni)
    _jobFinished = Signal(str, object, str)

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._events: List[Dict[str, Any]] = []
        self._ticker_events: List[Dict[str, Any]] = []
        self._ticker = ""
        self._is_busy = False
        self._busy_text = ""
        self._status = "Sinyaller henüz yüklenmedi"
        self._jobFinished.connect(self._on_job_finished)

    def _svc(self, name: str):
        return getattr(self._container, name, None) if self._container else None

    # ------------------------------------------------------------------ properties

    @Property("QVariantList", constant=True)
    def periodOptions(self) -> list:
        return [{"label": label, "days": days} for label, days in PERIOD_OPTIONS]

    @Property("QVariantList", constant=True)
    def typeOptions(self) -> list:
        return [{"label": label, "key": key} for label, key in TYPE_OPTIONS]

    @Property("QVariantList", notify=eventsChanged)
    def events(self) -> list:
        return self._events

    @Property("QVariantList", notify=tickerEventsChanged)
    def tickerEvents(self) -> list:
        return self._ticker_events

    @Property(str, notify=tickerEventsChanged)
    def tickerName(self) -> str:
        return self._ticker

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=busyChanged)
    def busyText(self) -> str:
        return self._busy_text

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, constant=True)
    def serviceAvailable(self) -> bool:
        return self._svc("technical_analysis_service") is not None

    @Property(bool, constant=True)
    def tvAvailable(self) -> bool:
        return self._svc("tv_backfill_service") is not None

    def _set_status(self, text: str) -> None:
        self._status = text
        self.statusChanged.emit()

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self._is_busy = busy
        self._busy_text = text if busy else ""
        self.busyChanged.emit()

    # ------------------------------------------------------------------ slots

    @Slot(int, str)
    def refresh(self, days: int, cross_type: str) -> None:
        """Kayıtlı sinyalleri listeler (hızlı DB okuması, ana thread'de)."""
        service = self._svc("technical_analysis_service")
        if service is None:
            self._set_status("Teknik analiz servisi bulunamadı")
            return
        try:
            kind = CrossType(cross_type) if cross_type else None
            events = service.get_recent_events(days=days if days > 0 else _ALL_DAYS, cross_type=kind, limit=500)
        except Exception as exc:
            logger.exception("Golden Cross sinyalleri okunamadı: %s", exc)
            self._events = []
            self.eventsChanged.emit()
            self._set_status(f"Sinyaller okunamadı: {exc}")
            return
        self._events = [self._event_to_dict(e) for e in events]
        self.eventsChanged.emit()
        self._set_status(f"{len(self._events)} sinyal listelendi")

    @Slot()
    def scanAll(self) -> None:
        service = self._svc("technical_analysis_service")
        if service is None or self._is_busy:
            return
        self._set_busy(True, "Golden Cross taraması çalışıyor...")
        self._submit("scan", service.scan_all)

    @Slot()
    def completeData(self) -> None:
        """Tüm BIST için eksik kapanışları son günden bugüne tamamlar."""
        service = self._svc("price_data_health_service")
        if service is None:
            self.notification.emit(False, "Fiyat verisi yönetim servisi bulunamadı.")
            return
        if self._is_busy:
            return
        from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_BIST

        calendar = self._svc("trading_calendar")
        target = date.today() - timedelta(days=1)
        while calendar is not None and not calendar.is_trading_day(target):
            target -= timedelta(days=1)
        self._set_busy(True, "Eksik fiyat verisi tamamlanıyor...")
        self._submit("backfill", service.update_from_latest_to_today, target, PRICE_SCOPE_ALL_BIST)

    @Slot()
    def loadFromTradingView(self) -> None:
        service = self._svc("tv_backfill_service")
        if service is None:
            self.notification.emit(False, "TradingView veri modülü kurulu değil.")
            return
        if self._is_busy:
            return
        end = date.today()
        start = end - timedelta(days=int(_TV_BACKFILL_YEARS * 365.25))
        self._set_busy(True, "TradingView'den geçmiş veri yükleniyor...")
        self._submit("tv_backfill", service.backfill_range, start, end)

    @Slot(str)
    def loadTickerEvents(self, ticker: str) -> None:
        clean = _clean_ticker(ticker)
        service = self._svc("technical_analysis_service")
        if service is None or not clean:
            return
        try:
            events = service.get_events_for_ticker(f"{clean}.IS") or service.get_events_for_ticker(clean)
        except Exception as exc:
            logger.exception("Hisse sinyal geçmişi okunamadı (%s): %s", clean, exc)
            events = []
        self._ticker = clean
        self._ticker_events = [self._event_to_dict(e) for e in events]
        self.tickerEventsChanged.emit()

    # ------------------------------------------------------------------ iç işleyiş

    def _submit(self, job: str, fn: Callable, *args) -> None:
        def work() -> None:
            try:
                self._jobFinished.emit(job, fn(*args), "")
            except Exception as exc:
                logger.exception("Golden Cross işi başarısız (%s): %s", job, exc)
                self._jobFinished.emit(job, None, str(exc))

        self._executor.submit(work)

    def _on_job_finished(self, job: str, result: Any, error: str) -> None:
        self._set_busy(False)
        if error:
            self._set_status(f"Hata: {error}")
            self.notification.emit(False, f"İşlem başarısız: {error}")
            return
        if job == "scan":
            message = (
                f"Tarama tamamlandı: {result.scanned_count} hisse, {result.new_event_count} yeni sinyal, "
                f"{result.skipped_count} atlandı (yetersiz veri)."
            )
            self._set_status(message)
            self.notification.emit(True, message)
            self.scanCompleted.emit()
        elif job == "backfill":
            count = getattr(result, "updated_count", 0)
            message = f"Veri tamamlama bitti: {count} fiyat kaydı eklendi."
            self._set_status(message)
            self.notification.emit(True, message)
            if count:
                self.pricesUpdated.emit()
        elif job == "tv_backfill":
            message = f"TradingView yükleme tamamlandı: {result} kayıt."
            self._set_status(message)
            self.notification.emit(True, message)
            self.pricesUpdated.emit()

    @staticmethod
    def _event_to_dict(e) -> Dict[str, Any]:
        is_golden = e.cross_type == CrossType.GOLDEN
        return {
            "ticker": _clean_ticker(e.ticker),
            "date": e.cross_date.strftime("%d.%m.%Y"),
            "type": e.cross_type.value,
            "typeLabel": "Golden" if is_golden else "Death",
            "isGolden": is_golden,
            "close": _fmt(e.close_price),
            "ma": f"{_fmt(e.short_ma)} / {_fmt(e.long_ma)}",
        }
