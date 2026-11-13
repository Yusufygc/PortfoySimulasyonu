"""NewsPanel.qml: dolu/boş/hata durumları uyarısız yüklenir, sekme geçişi ve bağlantı açma çalışır."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from tests.ui_qml.qobject_utils import children_of_class
from src.domain.models.news_item import NewsFeedResult, NewsSourceStatus
from src.ui_qml.controllers import url_opener as module
from src.ui_qml.controllers.news_controller import NewsController
from tests.ui_qml.test_news_controller import FakeNewsService, SyncExecutor, _item

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


def _pump(times: int = 8) -> None:
    for _ in range(times):
        QCoreApplication.processEvents()


def _panel(qapp, service):
    engine = QQmlApplicationEngine()
    controller = NewsController(
        container=SimpleNamespace(news_service=service, news_target_service=SimpleNamespace(get_targets=lambda: [])),
        parent=engine,
    )
    controller._executor = SyncExecutor()
    engine.rootContext().setContextProperty("newsController", controller)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "NewsPanel.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    assert item is not None
    item._engine, item._component = engine, component  # nesneler kapsam dışına çıkıp silinmesin
    item.setProperty("width", 380)
    item.setProperty("height", 520)
    _pump()
    return item, controller, warnings


def _list_count(item) -> int:
    lists = children_of_class(item, "ListView")
    return int(lists[0].property("count"))


def test_loads_without_warnings_before_first_fetch(qapp):
    item, controller, warnings = _panel(qapp, FakeNewsService())
    assert warnings == [] and _list_count(item) == 0


def test_company_and_market_tabs_show_their_rows(qapp):
    company = NewsFeedResult((_item("a"), _item("b", 10)), (NewsSourceStatus("kap"),))
    item, controller, warnings = _panel(qapp, FakeNewsService(company=company))
    controller.refresh()
    _pump()
    assert _list_count(item) == 2
    item.setProperty("currentTab", 1)
    _pump()
    assert _list_count(item) == 1  # piyasa akışında tek haber
    assert warnings == []


def test_empty_result_and_failed_sources_render_without_warnings(qapp):
    failed = NewsFeedResult((), (NewsSourceStatus("kap", error="HTTP 500"),))
    item, controller, warnings = _panel(qapp, FakeNewsService(company=failed, market=NewsFeedResult()))
    controller.refresh()
    _pump()
    assert _list_count(item) == 0 and controller.failedSources == "KAP bildirimleri"
    assert warnings == []


def test_open_url_slot_receives_row_url(qapp, monkeypatch):
    opened = []
    monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
    item, controller, _ = _panel(qapp, FakeNewsService())
    controller.refresh()
    _pump()
    controller.openUrl(controller.companyNews.row_at(0)["url"])
    assert opened == ["https://ex.com/a"]
