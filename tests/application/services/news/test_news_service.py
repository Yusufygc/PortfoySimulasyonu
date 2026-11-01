"""NewsService: kaynak yalıtımı, tekilleştirme, sıralama, önbellek TTL ve aç/kapa (sahte sağlayıcılar)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from src.application.services.news.news_service import NewsService
from src.domain.models.news_item import (
    NewsItem,
    NewsScope,
    NewsSourceConfig,
    NewsSourceKind,
    NewsTarget,
    TargetKind,
)
from src.domain.ports.repositories.i_news_source_repo import INewsCache, INewsSourceRepository
from src.domain.ports.services.i_news_provider import INewsProvider, NewsProviderUnavailable

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _item(title: str, source: str = "s", minutes: int = 0, url: str | None = None) -> NewsItem:
    return NewsItem(
        title=title, url=url or f"https://ex.com/{title}", source_id=source, source_name=source,
        published_at=T0 - timedelta(minutes=minutes),
    )


class MemoryRepo(INewsSourceRepository):
    def __init__(self) -> None:
        self.rows: Dict[str, NewsSourceConfig] = {}

    def list_sources(self):
        return list(self.rows.values())

    def save_source(self, config):
        self.rows[config.source_id] = config

    def delete_source(self, source_id):
        self.rows.pop(source_id, None)


class MemoryCache(INewsCache):
    def __init__(self) -> None:
        self.data: Dict[str, dict] = {}

    def load(self, key):
        return self.data.get(key)

    def store(self, key, fetched_at, items):
        self.data[key] = {"fetched_at": fetched_at, "items": list(items)}


class FakeProvider(INewsProvider):
    def __init__(self, config: NewsSourceConfig, items=None, error: str = "") -> None:
        self._config = config
        self.items = items or []
        self.error = error
        self.calls = 0

    source_id = property(lambda self: self._config.source_id)
    display_name = property(lambda self: self._config.name)
    scope = property(lambda self: self._config.scope)

    def fetch(self, targets):
        self.calls += 1
        if self.error:
            raise NewsProviderUnavailable(self.error)
        return list(self.items)


class Harness:
    def __init__(self, configs: List[NewsSourceConfig]) -> None:
        self.repo = MemoryRepo()
        self.cache = MemoryCache()
        self.providers: Dict[str, FakeProvider] = {}
        self.now = T0
        self.configs = configs
        self.service = NewsService(
            self.repo, lambda config: self.providers.get(config.source_id), self.cache,
            default_sources=lambda: self.configs, clock=lambda: self.now,
        )

    def provider(self, source_id: str, items=None, error: str = "") -> FakeProvider:
        config = next(c for c in self.configs if c.source_id == source_id)
        self.providers[source_id] = FakeProvider(config, items, error)
        return self.providers[source_id]


def _config(source_id: str, scope: NewsScope, enabled: bool = True) -> NewsSourceConfig:
    return NewsSourceConfig(source_id, NewsSourceKind.RSS, source_id, enabled, "tr", scope, "https://ex.com/" + source_id)


TARGETS = [NewsTarget("THYAO", "THY", TargetKind.BIST)]


def test_defaults_seeded_once_and_scope_split():
    h = Harness([_config("a", NewsScope.COMPANY), _config("m", NewsScope.MARKET)])
    h.provider("a", [_item("company")])
    h.provider("m", [_item("market")])
    assert [i.title for i in h.service.get_company_news(TARGETS).items] == ["company"]
    assert [i.title for i in h.service.get_market_news().items] == ["market"]
    assert len(h.repo.rows) == 2


def test_failing_source_isolated_and_reported():
    h = Harness([_config("ok", NewsScope.MARKET), _config("bad", NewsScope.MARKET)])
    h.provider("ok", [_item("fine")])
    h.provider("bad", error="HTTP 404")
    result = h.service.get_market_news()
    assert [i.title for i in result.items] == ["fine"]
    assert result.failed_sources == ("bad",)
    assert "404" in next(s for s in result.statuses if s.source_id == "bad").error


def test_unexpected_exception_does_not_break_other_sources():
    h = Harness([_config("ok", NewsScope.MARKET), _config("boom", NewsScope.MARKET)])
    h.provider("ok", [_item("fine")])
    broken = h.provider("boom")
    broken.fetch = lambda targets: (_ for _ in ()).throw(RuntimeError("beklenmedik"))
    result = h.service.get_market_news()
    assert len(result.items) == 1 and result.failed_sources == ("boom",)


def test_dedupe_by_url_keeps_newest_and_sorts_descending():
    h = Harness([_config("a", NewsScope.MARKET), _config("b", NewsScope.MARKET)])
    h.provider("a", [_item("same", "a", minutes=30, url="https://ex.com/x"), _item("older", "a", minutes=60)])
    h.provider("b", [_item("same", "b", minutes=5, url="https://ex.com/x"), _item("newest", "b", minutes=1)])
    titles = [(i.title, i.source_id) for i in h.service.get_market_news().items]
    assert titles == [("newest", "b"), ("same", "b"), ("older", "a")]


def test_cache_ttl_avoids_refetch_and_force_bypasses():
    h = Harness([_config("m", NewsScope.MARKET)])
    provider = h.provider("m", [_item("x")])
    h.service.get_market_news()
    h.now = T0 + timedelta(minutes=5)
    result = h.service.get_market_news()
    assert provider.calls == 1 and result.statuses[0].from_cache
    h.service.get_market_news(force=True)
    assert provider.calls == 2
    h.now = T0 + timedelta(minutes=20)
    h.service.get_market_news()
    assert provider.calls == 3


def test_error_falls_back_to_stale_cache_with_error_status():
    h = Harness([_config("m", NewsScope.MARKET)])
    provider = h.provider("m", [_item("cached")])
    h.service.get_market_news()
    provider.error = "bağlantı yok"
    h.now = T0 + timedelta(minutes=30)
    result = h.service.get_market_news()
    assert [i.title for i in result.items] == ["cached"]
    assert result.failed_sources == ("m",) and result.statuses[0].from_cache


def test_disabled_source_not_called_and_not_shown():
    h = Harness([_config("m", NewsScope.MARKET)])
    provider = h.provider("m", [_item("x")])
    h.service.get_market_news()
    h.service.set_source_enabled("m", False)
    result = h.service.get_market_news(force=True)
    assert result.items == () and provider.calls == 1
    h.service.set_source_enabled("m", True)
    assert len(h.service.get_market_news().items) == 1


def test_company_cache_key_depends_on_targets():
    h = Harness([_config("a", NewsScope.COMPANY)])
    provider = h.provider("a", [_item("x")])
    h.service.get_company_news(TARGETS)
    h.service.get_company_news([NewsTarget("AAPL", "Apple", TargetKind.US_STOCK)])
    assert provider.calls == 2


def test_unknown_source_enable_raises():
    h = Harness([_config("m", NewsScope.MARKET)])
    import pytest

    with pytest.raises(ValueError):
        h.service.set_source_enabled("yok", True)


def test_unsupported_provider_reported():
    h = Harness([_config("m", NewsScope.MARKET)])  # fabrikada sağlayıcı kayıtlı değil -> None
    result = h.service.get_market_news()
    assert result.failed_sources == ("m",)
