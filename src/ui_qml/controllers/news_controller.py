"""
NewsController — Genel Bakış haber paneli (QML): şirket haberleri ve piyasa/global haberleri.

Haberler arka plan iş parçacığında çekilir (tek işçi); sonuç Signal ile ana iş parçacığına döner. Kaynaklar
`NewsService` içinde önbelleklenir (yaklaşık 10 dk), bu yüzden sık yenileme kaynakları gereksiz yüklemez.
Ağ tamamen kapalıysa son başarılı çekim gösterilmeye devam eder ve ulaşılamayan kaynaklar bildirilir.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, QSettings, QTimer, Signal, Slot

from src.domain.models.news_item import NewsFeedResult, NewsItem
from src.ui_qml.controllers.news_settings_controller import load_refresh_minutes
from src.ui_qml.controllers.url_opener import open_external_url
from src.ui_qml.models.news_list_model import NewsListModel
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

_STARTUP_DELAY_MS = 2500


def relative_time_text(published: datetime, now: datetime | None = None) -> str:
    """Yayın zamanını göreli ve kısa gösterir ("5 dk önce", "3 sa önce", "2 gün önce", ardından tarih)."""
    reference = now or datetime.now(timezone.utc)
    seconds = int((reference - published).total_seconds())
    if seconds < 60:
        return msg("news.time.now")
    if seconds < 3600:
        return msg("news.time.minutes", n=seconds // 60)
    if seconds < 86400:
        return msg("news.time.hours", n=seconds // 3600)
    if seconds < 7 * 86400:
        return msg("news.time.days", n=seconds // 86400)
    return published.astimezone().strftime("%d.%m.%Y")


def news_item_to_row(item: NewsItem, now: datetime | None = None) -> Dict[str, Any]:
    return {
        "title": item.title,
        "summary": item.summary,
        "sourceName": item.source_name,
        "sourceId": item.source_id,
        "timeText": relative_time_text(item.published_at, now),
        "url": item.url,
        "symbols": ", ".join(item.related_symbols),
        "language": item.language,
        "badge": item.badge,
    }


class NewsController(QObject):
    """QML context property: newsController"""

    loadingChanged = Signal()
    failedSourcesChanged = Signal()
    updated = Signal()

    _fetchFinished = Signal(object, object)

    def __init__(
        self, container=None, parent: QObject | None = None, autostart: bool = False, settings: QSettings | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings or QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._company = NewsListModel(self)
        self._market = NewsListModel(self)
        self._loading = False
        self._pending_force = False
        self._loaded_once = False
        self._failed: List[str] = []
        self._fetchFinished.connect(self._on_fetch_finished)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        if self._service is not None and autostart:
            self._timer.start(self._interval_ms())
            QTimer.singleShot(_STARTUP_DELAY_MS, self.refresh)

    @property
    def _service(self):
        return getattr(self._container, "news_service", None) if self._container else None

    @property
    def _targets(self):
        return getattr(self._container, "news_target_service", None) if self._container else None

    # ---------- QML ---------- #

    @Property(QObject, constant=True)
    def companyNews(self) -> QObject:
        return self._company

    @Property(QObject, constant=True)
    def marketNews(self) -> QObject:
        return self._market

    @Property(bool, notify=loadingChanged)
    def isLoading(self) -> bool:
        return self._loading

    @Property(bool, notify=updated)
    def hasLoaded(self) -> bool:
        return self._loaded_once

    @Property(str, notify=failedSourcesChanged)
    def failedSources(self) -> str:
        """Ulaşılamayan kaynak adları (virgülle ayrılmış); hepsi sağlıklıysa boş."""
        return ", ".join(self._failed)

    @Slot()
    def refresh(self) -> None:
        self._start(force=False)

    @Slot()
    def forceRefresh(self) -> None:
        self._start(force=True)

    @Slot(int)
    def setRefreshMinutes(self, minutes: int) -> None:
        """Ayarlar'dan yenileme aralığı değişince zamanlayıcı yeni aralıkla yeniden başlar."""
        if self._timer.isActive():
            self._timer.start(max(1, int(minutes)) * 60_000)

    def _interval_ms(self) -> int:
        return load_refresh_minutes(self._settings) * 60_000

    @Slot(str)
    def openUrl(self, url: str) -> None:
        open_external_url(url)

    # ---------- Çekim ---------- #

    def _start(self, force: bool) -> None:
        service = self._service
        if service is None:
            return
        if self._loading:
            self._pending_force = self._pending_force or force
            return
        self._loading = True
        self.loadingChanged.emit()
        targets_service = self._targets

        def work() -> None:
            try:
                targets = targets_service.get_targets() if targets_service is not None else []
                company = service.get_company_news(targets, force=force)
                market = service.get_market_news(force=force)
                self._fetchFinished.emit(company, market)
            except Exception as exc:
                logger.warning("Haber akışı yenilenemedi: %s", exc, exc_info=True)
                self._fetchFinished.emit(None, None)

        self._executor.submit(work)

    def _on_fetch_finished(self, company: NewsFeedResult | None, market: NewsFeedResult | None) -> None:
        self._loading = False
        self.loadingChanged.emit()
        if company is not None and market is not None:
            now = datetime.now(timezone.utc)
            self._company.set_rows([news_item_to_row(i, now) for i in company.items])
            self._market.set_rows([news_item_to_row(i, now) for i in market.items])
            self._loaded_once = True
            self._set_failed(self._failed_names(company) + self._failed_names(market))
            self.updated.emit()
        if self._pending_force:
            self._pending_force = False
            self._start(force=True)

    def _failed_names(self, result: NewsFeedResult) -> List[str]:
        names = {c.source_id: c.name for c in self._service.list_sources()} if self._service else {}
        return [names.get(source_id, source_id) for source_id in result.failed_sources]

    def _set_failed(self, names: List[str]) -> None:
        if names != self._failed:
            self._failed = names
            self.failedSourcesChanged.emit()
