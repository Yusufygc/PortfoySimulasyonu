"""NewsSettingsController ve Ayarlar > Haber Kaynakları sekmesi (gerçek NewsService, bellek içi depo)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QSettings, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from tests.ui_qml.qobject_utils import children_of_class
from src.domain.models.news_item import NewsScope, NewsSourceConfig, NewsSourceKind, NewsSourceStatus
from src.ui_qml.controllers.news_controller import NewsController
from src.ui_qml.controllers.news_settings_controller import (
    DEFAULT_REFRESH_MINUTES,
    NewsSettingsController,
    status_text,
)
from tests.application.services.news.test_news_service import FakeProvider, Harness, _item
from tests.ui_qml.test_news_controller import SyncExecutor

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


def _settings(tmp_path) -> QSettings:
    return QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)


def _configs():
    return [
        NewsSourceConfig("kap", NewsSourceKind.KAP, "KAP bildirimleri", True, "tr", NewsScope.COMPANY),
        NewsSourceConfig("rss:a", NewsSourceKind.RSS, "A", True, "en", NewsScope.MARKET, "https://ex.com/a"),
    ]


def _controller(tmp_path, harness=None):
    harness = harness or Harness(_configs())
    harness.provider("kap", [_item("k")])
    harness.provider("rss:a", [_item("a")])
    container = SimpleNamespace(news_service=harness.service)
    ctrl = NewsSettingsController(container=container, settings=_settings(tmp_path))
    ctrl._executor = SyncExecutor()
    return ctrl, harness


class TestStatusText:
    def test_variants(self):
        now = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
        assert status_text(None) == "Henüz çekilmedi"
        assert status_text(NewsSourceStatus("a", now, 7)) == "Son çekim 12:00, 7 haber"  # İstanbul saati
        assert "HTTP 500" in status_text(NewsSourceStatus("a", error="HTTP 500"))
        assert "önbellek" in status_text(NewsSourceStatus("a", now, 3, "HTTP 500", True))


class TestSources:
    def test_rows_expose_flags(self, qapp, tmp_path):
        ctrl, _ = _controller(tmp_path)
        rows = {r["sourceId"]: r for r in ctrl.sources}
        assert rows["kap"]["isCompany"] and rows["kap"]["isKap"] and not rows["kap"]["massNotices"]
        assert rows["rss:a"]["language"] == "en" and rows["rss:a"]["description"] == "https://ex.com/a"

    def test_toggle_persists_and_hides_from_feed(self, qapp, tmp_path):
        ctrl, h = _controller(tmp_path)
        changed = []
        ctrl.sourcesChanged.connect(lambda: changed.append(1))
        ctrl.setSourceEnabled("rss:a", False)
        assert {r["sourceId"]: r["enabled"] for r in ctrl.sources}["rss:a"] is False and changed
        assert h.service.get_market_news().items == ()

    def test_mass_notice_option_roundtrip(self, qapp, tmp_path):
        ctrl, _ = _controller(tmp_path)
        ctrl.setMassNotices(True)
        assert next(r for r in ctrl.sources if r["isKap"])["massNotices"] is True
        ctrl.setMassNotices(False)
        assert next(r for r in ctrl.sources if r["isKap"])["massNotices"] is False

    def test_add_and_remove_custom_feed_with_error_notification(self, qapp, tmp_path):
        ctrl, _ = _controller(tmp_path)
        messages = []
        ctrl.notify.connect(lambda ok, msg: messages.append((ok, msg)))
        ctrl.addRssFeed("Özel", "ftp://x", "tr")
        assert messages[-1][0] is False and "http" in messages[-1][1]
        ctrl.addRssFeed("Özel", "https://ex.com/f", "tr")
        custom = next(r for r in ctrl.sources if r["isCustom"])
        ctrl.removeSource(custom["sourceId"])
        assert not any(r["isCustom"] for r in ctrl.sources)
        ctrl.removeSource("kap")  # varsayılan kaynak silinemez
        assert messages[-1][0] is False and any(r["sourceId"] == "kap" for r in ctrl.sources)


class TestConnectionTest:
    def test_success_and_failure_notify_and_update_status(self, qapp, tmp_path):
        ctrl, h = _controller(tmp_path)
        messages = []
        ctrl.notify.connect(lambda ok, msg: messages.append((ok, msg)))
        ctrl.testSource("rss:a")
        assert messages[-1][0] is True and "1 haber" in messages[-1][1] and not ctrl.isTesting
        h.providers["rss:a"].error = "HTTP 404"
        ctrl.testSource("rss:a")
        assert messages[-1][0] is False and "404" in messages[-1][1]
        assert next(r for r in ctrl.sources if r["sourceId"] == "rss:a")["hasError"]

    def test_new_url_test_does_not_add_source(self, qapp, tmp_path):
        ctrl, h = _controller(tmp_path)
        h.service._factory = lambda config: FakeProvider(config, [_item("x")])
        messages = []
        ctrl.notify.connect(lambda ok, msg: messages.append(ok))
        ctrl.testNewUrl("https://ex.com/feed")
        ctrl.testNewUrl("javascript:1")
        assert messages == [True, False] and len(ctrl.sources) == 2


class TestRefreshInterval:
    def test_default_option_validation_and_signal(self, qapp, tmp_path):
        ctrl, _ = _controller(tmp_path)
        seen = []
        ctrl.refreshMinutesChanged.connect(seen.append)
        assert ctrl.refreshMinutes == DEFAULT_REFRESH_MINUTES
        ctrl.setRefreshMinutes(7)  # geçersiz seçenek yok sayılır
        ctrl.setRefreshMinutes(30)
        ctrl.setRefreshMinutes(30)  # değişmedi: sinyal yok
        assert ctrl.refreshMinutes == 30 and seen == [30]

    def test_news_controller_timer_follows_setting(self, qapp, tmp_path):
        settings = _settings(tmp_path)
        settings.setValue("news/refresh_minutes", 15)
        container = SimpleNamespace(news_service=object(), news_target_service=None)
        ctrl = NewsController(container=container, autostart=True, settings=settings)
        assert ctrl._timer.interval() == 15 * 60_000
        ctrl.setRefreshMinutes(5)
        assert ctrl._timer.interval() == 5 * 60_000


def _pump(times: int = 8) -> None:
    for _ in range(times):
        QCoreApplication.processEvents()


def test_settings_tab_loads_without_warnings_and_lists_sources(qapp, tmp_path):
    ctrl, _ = _controller(tmp_path)
    engine = QQmlApplicationEngine()
    ctrl.setParent(engine)
    engine.rootContext().setContextProperty("newsSettingsController", ctrl)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "SettingsNewsTab.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    item._engine, item._component = engine, component
    item.setProperty("width", 900)
    _pump()
    repeaters = children_of_class(item, "Repeater")
    assert sorted(int(r.property("count")) for r in repeaters) == [1, 1]  # şirket grubunda KAP, piyasa grubunda rss:a
    ctrl.setSourceEnabled("rss:a", False)
    _pump()
    assert warnings == []
