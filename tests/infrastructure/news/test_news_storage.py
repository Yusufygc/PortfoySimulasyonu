"""Haber kaynağı tercih deposu (SQLite) ve JSON dosya önbelleği."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.models.news_item import NewsItem, NewsScope, NewsSourceConfig, NewsSourceKind
from src.infrastructure.db.sqlalchemy.orm_models import Base
from src.infrastructure.db.sqlalchemy.repositories.sa_news_source_repository import SQLAlchemyNewsSourceRepository
from src.infrastructure.news.default_sources import default_news_sources
from src.infrastructure.news.news_file_cache import JsonFileNewsCache
from src.infrastructure.news.provider_factory import NewsProviderFactory


class _Provider:
    """SQLAlchemyEngineProvider'ın get_session sözleşmesini bellek içi SQLite ile karşılar."""

    def __init__(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self._factory = sessionmaker(bind=engine)

    def get_session(self):
        return self._factory()


@pytest.fixture()
def repo():
    return SQLAlchemyNewsSourceRepository(_Provider())


def test_save_list_update_delete_roundtrip(repo):
    config = NewsSourceConfig(
        "rss:x", NewsSourceKind.RSS, "X", True, "en", NewsScope.MARKET, "https://x.com/rss", "açıklama", True,
        {"include_mass_notices": "true"},
    )
    repo.save_source(config)
    assert repo.list_sources() == [config]
    repo.save_source(NewsSourceConfig("rss:x", NewsSourceKind.RSS, "X", False, "en", NewsScope.MARKET, "https://x.com/rss"))
    assert repo.list_sources()[0].enabled is False
    repo.delete_source("rss:x")
    repo.delete_source("rss:yok")  # olmayan kaynağı silmek hata değildir
    assert repo.list_sources() == []


def test_list_keeps_insertion_order(repo):
    for config in default_news_sources():
        repo.save_source(config)
    assert [c.source_id for c in repo.list_sources()] == [c.source_id for c in default_news_sources()]


def test_default_sources_are_consistent():
    sources = default_news_sources()
    ids = [s.source_id for s in sources]
    assert len(ids) == len(set(ids))
    assert {s.source_id for s in sources if s.scope is NewsScope.COMPANY} == {"kap", "yahoo_rss", "google_news"}
    assert all(s.url.startswith("https://") for s in sources if s.kind is NewsSourceKind.RSS)
    assert not {s.enabled for s in sources if s.source_id in ("rss:coindesk", "rss:cointelegraph")} - {False}


def test_factory_builds_provider_for_every_default_source():
    factory = NewsProviderFactory(lambda ticker: "oid")
    for config in default_news_sources():
        provider = factory(config)
        assert provider is not None and provider.source_id == config.source_id
        assert provider.scope is config.scope


def test_factory_reads_kap_mass_notice_option():
    factory = NewsProviderFactory(lambda ticker: "oid")
    kap = next(c for c in default_news_sources() if c.source_id == "kap")
    from dataclasses import replace

    assert factory(kap)._include_mass is False
    assert factory(replace(kap, options={"include_mass_notices": "true"}))._include_mass is True


def test_file_cache_roundtrip_and_corruption(tmp_path):
    cache = JsonFileNewsCache(tmp_path)
    assert cache.load("k") is None
    item = NewsItem(
        "Başlık", "https://ex.com/1", "kap", "KAP", datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc), "özet",
        ("THYAO",), "tr", "ODA",
    )
    fetched = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
    cache.store("k", fetched, [item])
    loaded = cache.load("k")
    assert loaded["items"] == [item] and loaded["fetched_at"] == fetched
    next(tmp_path.iterdir()).write_text("{bozuk", encoding="utf-8")
    assert cache.load("k") is None
