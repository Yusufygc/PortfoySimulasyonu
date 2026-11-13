"""NewsController: yükleme akışı, hata gösterimi, göreli zaman ve güvenli bağlantı açma (sahte servislerle)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication

from src.domain.models.news_item import NewsFeedResult, NewsItem, NewsSourceStatus
from src.ui_qml.controllers import url_opener as module
from src.ui_qml.controllers.news_controller import NewsController, news_item_to_row, relative_time_text

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


class SyncExecutor:
    def submit(self, fn):
        fn()


def _item(title, minutes=5, symbols=("THYAO",), lang="tr"):
    return NewsItem(
        title, f"https://ex.com/{title}", "kap", "KAP", NOW - timedelta(minutes=minutes), "özet", symbols, lang, "ODA"
    )


class FakeNewsService:
    def __init__(self, company=None, market=None, fail=False):
        self.company = company or NewsFeedResult((_item("a"),), (NewsSourceStatus("kap"),))
        self.market = market or NewsFeedResult((_item("m", symbols=()),), (NewsSourceStatus("rss:x"),))
        self.fail = fail
        self.calls = []

    def get_company_news(self, targets, force=False):
        self.calls.append(("company", tuple(targets), force))
        if self.fail:
            raise RuntimeError("ağ yok")
        return self.company

    def get_market_news(self, force=False):
        self.calls.append(("market", (), force))
        return self.market

    def list_sources(self):
        return [SimpleNamespace(source_id="kap", name="KAP bildirimleri"), SimpleNamespace(source_id="rss:x", name="X")]


def _controller(qapp, service):
    container = SimpleNamespace(
        news_service=service, news_target_service=SimpleNamespace(get_targets=lambda: ["T"])
    )
    ctrl = NewsController(container=container)
    ctrl._executor = SyncExecutor()
    return ctrl


class TestRelativeTime:
    @pytest.mark.parametrize(
        "delta,expected",
        [
            (timedelta(seconds=10), "şimdi"),
            (timedelta(minutes=5), "5 dk önce"),
            (timedelta(hours=3, minutes=20), "3 sa önce"),
            (timedelta(days=2), "2 gün önce"),
        ],
    )
    def test_relative(self, delta, expected):
        assert relative_time_text(NOW - delta, NOW) == expected

    def test_old_news_shows_date(self):
        assert relative_time_text(NOW - timedelta(days=30), NOW).count(".") == 2

    def test_row_fields(self):
        row = news_item_to_row(_item("a", symbols=("THYAO", "GARAN"), lang="en"), NOW)
        assert row["symbols"] == "THYAO, GARAN" and row["language"] == "en" and row["timeText"] == "5 dk önce"
        assert row["url"] == "https://ex.com/a" and row["badge"] == "ODA"


class TestRefresh:
    def test_refresh_fills_both_models_and_passes_targets(self, qapp):
        service = FakeNewsService()
        ctrl = _controller(qapp, service)
        assert not ctrl.hasLoaded
        ctrl.refresh()
        assert ctrl.companyNews.rowCount() == 1 and ctrl.marketNews.rowCount() == 1
        assert ctrl.hasLoaded and not ctrl.isLoading and ctrl.failedSources == ""
        assert service.calls[0] == ("company", ("T",), False)

    def test_force_refresh_passes_force(self, qapp):
        service = FakeNewsService()
        ctrl = _controller(qapp, service)
        ctrl.forceRefresh()
        assert all(call[2] for call in service.calls)

    def test_failed_sources_named_for_user(self, qapp):
        company = NewsFeedResult((), (NewsSourceStatus("kap", error="HTTP 500"),))
        market = NewsFeedResult((_item("m"),), (NewsSourceStatus("rss:x", error="HTTP 404"),))
        ctrl = _controller(qapp, FakeNewsService(company, market))
        ctrl.refresh()
        assert ctrl.failedSources == "KAP bildirimleri, X"

    def test_service_exception_keeps_previous_rows(self, qapp):
        service = FakeNewsService()
        ctrl = _controller(qapp, service)
        ctrl.refresh()
        service.fail = True
        ctrl.refresh()
        assert ctrl.companyNews.rowCount() == 1 and not ctrl.isLoading

    def test_without_service_is_inert(self, qapp):
        ctrl = NewsController(container=None)
        ctrl.refresh()
        assert not ctrl.isLoading and ctrl.companyNews.rowCount() == 0

    def test_autostart_is_off_by_default(self, qapp):
        assert not _controller(qapp, FakeNewsService())._timer.isActive()


class TestOpenUrl:
    def test_only_http_schemes_open(self, qapp, monkeypatch):
        opened = []
        monkeypatch.setattr(module.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True)
        ctrl = _controller(qapp, FakeNewsService())
        ctrl.openUrl("https://www.kap.org.tr/tr/Bildirim/1")
        ctrl.openUrl("file:///C:/Windows/system32/calc.exe")
        ctrl.openUrl("javascript:alert(1)")
        ctrl.openUrl("")
        assert opened == ["https://www.kap.org.tr/tr/Bildirim/1"]
