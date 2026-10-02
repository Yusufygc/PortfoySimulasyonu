"""
PriceDataController — Fiyat verisi sağlığı (analiz, eksik tamamlama, silme) QML controller'ı.

`PriceDataHealthService` üzerinden:
- Seçili kapsam (tüm aktif portföyler / ana portföy / model portföy) ve tarih aralığı için eksik gün analizi
- Toplu eksik güncelleme, seçili hisse güncelleme, "son günden bugüne" güncelleme
- Aralık silme ve raporu panoya kopyalama
Ağır işler arka plan thread'inde çalışır, sonuçlar Qt sinyalleriyle ana thread'e taşınır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from src.application.services.market.price_data_report_formatter import (
    display_ticker,
    format_report_html,
    format_report_text,
    format_stock_detail_html,
    is_healthy,
)

logger = logging.getLogger(__name__)

_DATE_FMT = "%d.%m.%Y"


def _parse_date(text: str) -> Optional[date]:
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", _DATE_FMT):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class PriceDataController(QObject):
    """QML context property: priceDataController"""

    busyChanged = Signal()
    scopeOptionsChanged = Signal()
    reportChanged = Signal()
    detailChanged = Signal()
    rangeChanged = Signal()
    # (success, message) — Ayarlar sekmesi toast'ı
    notification = Signal(bool, str, arguments=["success", "message"])
    # Yeni fiyat yazıldı; Dashboard/Model ekranları yenilenmeli
    pricesUpdated = Signal()

    # Worker -> ana thread köprüsü: (iş adı, sonuç, hata metni)
    _jobFinished = Signal(str, object, str)

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._service = getattr(container, "price_data_health_service", None) if container else None
        self._executor = ThreadPoolExecutor(max_workers=1)

        self._is_busy = False
        self._busy_text = ""
        self._scope_options: List[Dict[str, str]] = []
        self._report = None
        self._rows: List[Dict[str, Any]] = []
        self._problem_only = False
        self._detail_html = ""
        self._start_text = ""
        self._end_text = ""
        self._selected_stock_id = -1
        self._last_scope = "all_active"
        self._stock_count = "-"
        self._missing_count = "-"
        self._holiday_count = "-"
        self._candidate_count = "-"
        self._latest_date = "-"

        self._jobFinished.connect(self._on_job_finished)
        self._load_scope_options()
        self._reset_range()

    # ------------------------------------------------------------------ properties

    @Property(bool, constant=True)
    def serviceAvailable(self) -> bool:
        return self._service is not None

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=busyChanged)
    def busyText(self) -> str:
        return self._busy_text

    @Property("QVariantList", notify=scopeOptionsChanged)
    def scopeOptions(self) -> list:
        return self._scope_options

    @Property("QVariantList", notify=reportChanged)
    def rows(self) -> list:
        return self._rows

    @Property(bool, notify=reportChanged)
    def hasReport(self) -> bool:
        return self._report is not None

    @Property(bool, notify=reportChanged)
    def problemOnly(self) -> bool:
        return self._problem_only

    @Property(str, notify=detailChanged)
    def detailHtml(self) -> str:
        return self._detail_html

    @Property(str, notify=rangeChanged)
    def startText(self) -> str:
        return self._start_text

    @Property(str, notify=rangeChanged)
    def endText(self) -> str:
        return self._end_text

    @Property(int, notify=detailChanged)
    def selectedStockId(self) -> int:
        return self._selected_stock_id

    @Property(str, notify=reportChanged)
    def stockCount(self) -> str:
        return self._stock_count

    @Property(str, notify=reportChanged)
    def missingCount(self) -> str:
        return self._missing_count

    @Property(str, notify=reportChanged)
    def holidayCount(self) -> str:
        return self._holiday_count

    @Property(str, notify=reportChanged)
    def holidayCandidateCount(self) -> str:
        return self._candidate_count

    @Property(str, notify=reportChanged)
    def latestDate(self) -> str:
        return self._latest_date

    # ------------------------------------------------------------------ yardımcılar

    def _load_scope_options(self) -> None:
        options = [{"value": "all_active", "label": "Tüm aktif portföyler"},
                   {"value": "dashboard", "label": "Ana Portföy"}]
        if self._service is not None:
            try:
                options = [{"value": o.value, "label": o.label} for o in self._service.portfolio_scope_options()]
            except Exception as exc:
                logger.warning("Fiyat verisi kapsam seçenekleri okunamadı: %s", exc)
        self._scope_options = options
        self.scopeOptionsChanged.emit()

    def _reset_range(self, scope: Optional[str] = None) -> None:
        today = date.today()
        start = today - timedelta(days=30)
        if self._service is not None:
            try:
                start = self._service.default_start_date(today, scope)
            except Exception as exc:
                logger.debug("Varsayılan başlangıç tarihi okunamadı: %s", exc)
        self._start_text = start.strftime(_DATE_FMT)
        self._end_text = today.strftime(_DATE_FMT)
        self.rangeChanged.emit()

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self._is_busy = busy
        self._busy_text = text if busy else ""
        self.busyChanged.emit()

    def _resolve_range(self, start_text: str, end_text: str, scope: str) -> Optional[tuple]:
        """Tarih metinlerini doğrular; portföye ilk hisse eklenme tarihinden önceye inmez."""
        start, end = _parse_date(start_text), _parse_date(end_text)
        if start is None or end is None:
            self.notification.emit(False, "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY")
            return None
        if start > end:
            self.notification.emit(False, "Başlangıç tarihi bitiş tarihinden büyük olamaz.")
            return None
        try:
            minimum = self._service.minimum_start_date(scope)
        except Exception:
            minimum = None
        if minimum and start < minimum:
            start = minimum
            self._start_text = start.strftime(_DATE_FMT)
            self.rangeChanged.emit()
            self.notification.emit(
                False, f"Başlangıç tarihi portföye ilk hisse eklenme tarihinden önce olamaz ({minimum:{_DATE_FMT}})."
            )
        return start, end

    def _ready(self) -> bool:
        if self._service is None:
            self.notification.emit(False, "Fiyat verisi yönetim servisi kullanılamıyor.")
            return False
        return not self._is_busy

    def _run(self, job: str, busy_text: str, fn: Callable, *args) -> None:
        self._set_busy(True, busy_text)

        def work() -> None:
            try:
                self._jobFinished.emit(job, fn(*args), "")
            except Exception as exc:
                logger.exception("Fiyat verisi işlemi başarısız (%s): %s", job, exc)
                self._jobFinished.emit(job, None, str(exc))

        self._executor.submit(work)

    # ------------------------------------------------------------------ slots

    @Slot(str)
    def resetRange(self, scope: str) -> None:
        self._reset_range(scope or None)

    @Slot(str, str, str)
    def analyze(self, start_text: str, end_text: str, scope: str) -> None:
        if not self._ready():
            return
        resolved = self._resolve_range(start_text, end_text, scope)
        if resolved is None:
            return
        self._last_scope = scope
        self._run("analyze", "Veri sağlığı analiz ediliyor...", self._service.analyze, resolved[0], resolved[1], scope)

    @Slot(str, str, str)
    def updateMissing(self, start_text: str, end_text: str, scope: str) -> None:
        if not self._ready():
            return
        resolved = self._resolve_range(start_text, end_text, scope)
        if resolved is None:
            return
        self._last_scope = scope
        self._run("update", "Eksik fiyatlar güncelleniyor...", self._service.update_missing_prices,
                  resolved[0], resolved[1], None, scope)

    @Slot(int, str, str, str)
    def updateSelected(self, stock_id: int, start_text: str, end_text: str, scope: str) -> None:
        if stock_id <= 0:
            self.notification.emit(False, "Önce tablodan bir hisse seçin.")
            return
        if not self._ready():
            return
        resolved = self._resolve_range(start_text, end_text, scope)
        if resolved is None:
            return
        self._last_scope = scope
        self._run("update", "Seçili hisse güncelleniyor...", self._service.update_stock_range,
                  stock_id, resolved[0], resolved[1])

    @Slot(str)
    def updateFromLatest(self, scope: str) -> None:
        if not self._ready():
            return
        calendar = getattr(self._container, "trading_calendar", None) if self._container else None
        target = date.today() - timedelta(days=1)
        while calendar is not None and not calendar.is_trading_day(target):
            target -= timedelta(days=1)
        self._last_scope = scope
        self._run("update", "Son güncel günden bugüne eksikler tamamlanıyor...",
                  self._service.update_from_latest_to_today, target, scope)

    @Slot(str, str, str)
    def deleteRange(self, start_text: str, end_text: str, scope: str) -> None:
        """Onay QML tarafında alınır; bu slot doğrudan siler."""
        if not self._ready():
            return
        resolved = self._resolve_range(start_text, end_text, scope)
        if resolved is None:
            return
        self._last_scope = scope
        self._run("delete", "Fiyat kayıtları siliniyor...", self._service.delete_range,
                  resolved[0], resolved[1], scope)

    @Slot(int)
    def selectStock(self, stock_id: int) -> None:
        self._selected_stock_id = stock_id
        if self._report is not None:
            row = next((r for r in self._report.rows if r.stock_id == stock_id), None)
            if row is not None:
                self._detail_html = format_stock_detail_html(row, self._report)
        self.detailChanged.emit()

    @Slot(bool)
    def setProblemOnly(self, value: bool) -> None:
        self._problem_only = value
        self._rebuild_rows()
        self.reportChanged.emit()

    @Slot()
    def copyReport(self) -> None:
        if self._report is None:
            self.notification.emit(False, "Kopyalanacak analiz raporu yok. Önce analiz çalıştırın.")
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(format_report_text(self._report))
        self.notification.emit(True, "Veri sağlığı raporu panoya kopyalandı.")

    # ------------------------------------------------------------------ sonuç işleme

    def _on_job_finished(self, job: str, result: Any, error: str) -> None:
        self._set_busy(False)
        if error:
            self.notification.emit(False, f"İşlem başarısız: {error}")
            return
        if result is None:
            return
        if job == "analyze":
            self._apply_report(result)
            self.notification.emit(True, f"Analiz tamamlandı: {result.health_label}")
        elif job == "update":
            self._handle_update_result(result)
        elif job == "delete":
            self.notification.emit(True, f"{result} fiyat kaydı silindi.")
            self.pricesUpdated.emit()
            self._reanalyze()

    def _handle_update_result(self, result: Any) -> None:
        if result.updated_count:
            self.notification.emit(
                True,
                f"{result.updated_count} fiyat kaydı eklendi/güncellendi, {result.skipped_holiday_count} tatil günü atlandı.",
            )
            self.pricesUpdated.emit()
        else:
            self.notification.emit(False, "Güncellenecek fiyat kaydı bulunamadı.")
        if result.errors:
            self._detail_html = (
                "<b>Hata detayları:</b><br>" + "<br>".join(str(e) for e in result.errors[:30])
            )
            self.detailChanged.emit()
            self.notification.emit(False, f"Veri kaynağı uyarısı: {len(result.errors)} hata.")
        event_bus = getattr(self._container, "event_bus", None) if self._container else None
        if event_bus is not None and getattr(result, "prices", None):
            event_bus.prices_updated.emit(dict(result.prices))
        self._reanalyze()

    def _reanalyze(self) -> None:
        if self._report is not None:
            self.analyze(self._report.start_date.strftime(_DATE_FMT), self._report.end_date.strftime(_DATE_FMT),
                         self._last_scope)

    def _apply_report(self, report: Any) -> None:
        self._report = report
        self._stock_count = str(report.total_stock_count)
        self._missing_count = str(report.total_missing_count)
        self._holiday_count = str(report.known_holiday_count)
        self._candidate_count = str(report.holiday_candidate_count)
        self._latest_date = report.latest_price_date.strftime(_DATE_FMT) if report.latest_price_date else "-"
        self._selected_stock_id = -1
        self._detail_html = format_report_html(report)
        self._rebuild_rows()
        self.reportChanged.emit()
        self.detailChanged.emit()

    def _rebuild_rows(self) -> None:
        if self._report is None:
            self._rows = []
            return
        rows = []
        for row in self._report.rows:
            if self._problem_only and row.missing_count <= 0:
                continue
            rows.append({
                "stockId": row.stock_id,
                "ticker": display_ticker(row.ticker),
                "lastDate": row.last_price_date.strftime(_DATE_FMT) if row.last_price_date else "-",
                "missingCount": row.missing_count,
                "status": row.status,
                "healthy": is_healthy(row.status),
                "firstMissing": row.first_missing_date.strftime(_DATE_FMT) if row.first_missing_date else "-",
                "lastMissing": row.last_missing_date.strftime(_DATE_FMT) if row.last_missing_date else "-",
            })
        self._rows = rows
