"""
NewsSettingsController — Ayarlar > Haber Kaynakları (QML).

Kaynakları tek tek açıp kapatma, özel RSS ekleme/silme, KAP toplu bildirim seçeneği, bağlantı testi ve haber paneli
yenileme aralığı. Yalnızca `NewsService` üzerinden çalışır; ağ gerektiren testler arka planda yürür.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, QSettings, Signal, Slot

from src.qt_compat.user_settings import user_settings
from src.domain.market_clock import to_market_datetime
from src.domain.models.news_item import NewsScope, NewsSourceConfig, NewsSourceKind, NewsSourceStatus
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

REFRESH_MINUTES_KEY = "news/refresh_minutes"
REFRESH_OPTIONS = (5, 10, 15, 30, 60)
DEFAULT_REFRESH_MINUTES = 10
MASS_NOTICES_OPTION = "include_mass_notices"


def load_refresh_minutes(settings: QSettings) -> int:
    try:
        minutes = int(settings.value(REFRESH_MINUTES_KEY, DEFAULT_REFRESH_MINUTES))
    except (TypeError, ValueError):
        return DEFAULT_REFRESH_MINUTES
    return minutes if minutes in REFRESH_OPTIONS else DEFAULT_REFRESH_MINUTES


def status_text(status: NewsSourceStatus | None) -> str:
    if status is None:
        return msg("news_settings.never_fetched")
    if status.error:
        suffix = msg("news_settings.from_cache_suffix") if status.from_cache else ""
        return msg("news_settings.error", error=status.error, suffix=suffix)
    when = to_market_datetime(status.fetched_at).strftime("%H:%M") if status.fetched_at else ""
    if when:
        return msg("news_settings.last_fetch", when=when, count=status.item_count)
    return msg("news_settings.count_only", count=status.item_count)


def source_to_row(config: NewsSourceConfig, status: NewsSourceStatus | None) -> Dict[str, Any]:
    return {
        "sourceId": config.source_id,
        "name": config.name,
        "description": config.description or config.url,
        "language": config.language,
        "enabled": config.enabled,
        "isCustom": config.is_custom,
        "isCompany": config.scope is NewsScope.COMPANY,
        "isKap": config.kind is NewsSourceKind.KAP,
        "massNotices": str(config.options.get(MASS_NOTICES_OPTION, "")).lower() == "true",
        "statusText": status_text(status),
        "hasError": bool(status and status.error),
    }


class NewsSettingsController(QObject):
    """QML context property: newsSettingsController"""

    sourcesChanged = Signal()
    refreshMinutesChanged = Signal(int)
    notify = Signal(bool, str)
    testingChanged = Signal()

    _testFinished = Signal(str, object)

    def __init__(self, container=None, parent: QObject | None = None, settings: QSettings | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._settings = settings or user_settings()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._testing: set[str] = set()
        self._rows: List[Dict[str, Any]] = []
        self._testFinished.connect(self._on_test_finished)
        self._reload_rows()

    @property
    def _service(self):
        return getattr(self._container, "news_service", None) if self._container else None

    def _reload_rows(self) -> None:
        service = self._service
        if service is None:
            self._rows = []
            return
        try:
            self._rows = [source_to_row(c, service.get_status(c.source_id)) for c in service.list_sources()]
        except Exception as exc:
            logger.warning("Haber kaynakları okunamadı: %s", exc)
            self._rows = []

    # ---------- QML ---------- #

    @Property("QVariantList", notify=sourcesChanged)
    def sources(self) -> list:
        return self._rows

    @Property(int, notify=refreshMinutesChanged)
    def refreshMinutes(self) -> int:
        return load_refresh_minutes(self._settings)

    @Property("QVariantList", constant=True)
    def refreshOptions(self) -> list:
        return list(REFRESH_OPTIONS)

    @Property(bool, notify=testingChanged)
    def isTesting(self) -> bool:
        return bool(self._testing)

    @Slot()
    def reload(self) -> None:
        self._reload_rows()
        self.sourcesChanged.emit()

    @Slot(str, bool)
    def setSourceEnabled(self, source_id: str, enabled: bool) -> None:
        self._mutate(lambda s: s.set_source_enabled(source_id, enabled))

    @Slot(bool)
    def setMassNotices(self, enabled: bool) -> None:
        self._mutate(lambda s: s.set_source_option("kap", MASS_NOTICES_OPTION, "true" if enabled else "false"))

    @Slot(str, str, str)
    def addRssFeed(self, name: str, url: str, language: str) -> None:
        self._mutate(lambda s: s.add_rss_source(name, url, language))

    @Slot(str)
    def removeSource(self, source_id: str) -> None:
        self._mutate(lambda s: s.remove_source(source_id))

    @Slot(int)
    def setRefreshMinutes(self, minutes: int) -> None:
        if minutes not in REFRESH_OPTIONS or minutes == self.refreshMinutes:
            return
        self._settings.setValue(REFRESH_MINUTES_KEY, int(minutes))
        self._settings.sync()
        self.refreshMinutesChanged.emit(int(minutes))

    @Slot(str)
    def testSource(self, source_id: str) -> None:
        self._run_test(source_id, lambda s: s.test_source(source_id))

    @Slot(str)
    def testNewUrl(self, url: str) -> None:
        self._run_test("", lambda s: s.test_rss_url(url))

    # ---------- İç ---------- #

    def _mutate(self, operation) -> None:
        service = self._service
        if service is None:
            return
        try:
            operation(service)
        except ValueError as exc:
            self.notify.emit(False, str(exc))
            return
        except Exception as exc:
            logger.warning("Haber kaynağı işlemi başarısız: %s", exc, exc_info=True)
            self.notify.emit(False, msg("news_settings.operation_failed", error=exc))
            return
        self._reload_rows()
        self.sourcesChanged.emit()

    def _run_test(self, key: str, operation) -> None:
        service = self._service
        if service is None or key in self._testing:
            return
        self._testing.add(key)
        self.testingChanged.emit()

        def work() -> None:
            try:
                self._testFinished.emit(key, operation(service))
            except Exception as exc:
                logger.warning("Haber kaynağı testi başarısız: %s", exc, exc_info=True)
                self._testFinished.emit(key, NewsSourceStatus(key, error=f"{type(exc).__name__}: {exc}"))

        self._executor.submit(work)

    def _on_test_finished(self, key: str, status: NewsSourceStatus) -> None:
        self._testing.discard(key)
        self.testingChanged.emit()
        if status.ok:
            self.notify.emit(True, msg("news_settings.test_ok", count=status.item_count))
        else:
            self.notify.emit(False, msg("news_settings.test_failed", error=status.error))
        self._reload_rows()
        self.sourcesChanged.emit()
