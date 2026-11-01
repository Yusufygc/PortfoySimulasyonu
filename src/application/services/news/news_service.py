"""Haber akışı: etkin kaynakları paralel çeker, önbellekler, tekilleştirir ve tarihe göre sıralar."""
from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.domain.models.news_item import (
    NewsFeedResult,
    NewsItem,
    NewsScope,
    NewsSourceConfig,
    NewsSourceStatus,
    NewsTarget,
)
from src.domain.ports.repositories.i_news_source_repo import INewsCache, INewsSourceRepository
from src.domain.ports.services.i_news_provider import INewsProvider, NewsProviderUnavailable

logger = logging.getLogger(__name__)

DEFAULT_TTL = timedelta(minutes=10)
MAX_ITEMS = 150
_MAX_WORKERS = 6

ProviderFactory = Callable[[NewsSourceConfig], Optional[INewsProvider]]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_key(config: NewsSourceConfig, targets: Sequence[NewsTarget]) -> str:
    if config.scope is NewsScope.MARKET:
        return f"{config.source_id}|{config.url}"
    digest = hashlib.sha1("|".join(sorted(f"{t.kind.value}:{t.symbol}" for t in targets)).encode()).hexdigest()[:10]
    return f"{config.source_id}|{digest}"


class NewsService:
    def __init__(
        self,
        source_repo: INewsSourceRepository,
        provider_factory: ProviderFactory,
        cache: INewsCache,
        default_sources: Callable[[], List[NewsSourceConfig]],
        ttl: timedelta = DEFAULT_TTL,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._repo = source_repo
        self._factory = provider_factory
        self._cache = cache
        self._defaults = default_sources
        self._ttl = ttl
        self._clock = clock
        self._seeded = False

    # ---------- Kaynak yönetimi ---------- #

    def list_sources(self) -> List[NewsSourceConfig]:
        self._ensure_defaults()
        return self._repo.list_sources()

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        for config in self.list_sources():
            if config.source_id == source_id:
                self._repo.save_source(replace(config, enabled=enabled))
                return
        raise ValueError(f"Haber kaynağı bulunamadı: {source_id}")

    def _ensure_defaults(self) -> None:
        if self._seeded:
            return
        if not self._repo.list_sources():
            for config in self._defaults():
                self._repo.save_source(config)
        self._seeded = True

    # ---------- Akışlar ---------- #

    def get_company_news(self, targets: Sequence[NewsTarget], force: bool = False) -> NewsFeedResult:
        """Takip hedeflerine bağlı haberler (KAP, Yahoo, Google)."""
        return self._collect(NewsScope.COMPANY, targets, force)

    def get_market_news(self, force: bool = False) -> NewsFeedResult:
        """Sembolsüz genel piyasa ve global haber akışı (RSS)."""
        return self._collect(NewsScope.MARKET, (), force)

    def _collect(self, scope: NewsScope, targets: Sequence[NewsTarget], force: bool) -> NewsFeedResult:
        sources = [c for c in self.list_sources() if c.enabled and c.scope is scope]
        if not sources:
            return NewsFeedResult()
        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(sources))) as pool:
            results = list(pool.map(lambda config: self._load_source(config, targets, force), sources))
        statuses = tuple(status for _, status in results)
        return NewsFeedResult(items=self._merge(items for items, _ in results), statuses=statuses)

    def _load_source(
        self, config: NewsSourceConfig, targets: Sequence[NewsTarget], force: bool
    ) -> Tuple[List[NewsItem], NewsSourceStatus]:
        key = _cache_key(config, targets)
        cached = self._cache.load(key)
        now = self._clock()
        if cached and not force and now - cached["fetched_at"] < self._ttl:
            items = cached["items"]
            return items, NewsSourceStatus(config.source_id, cached["fetched_at"], len(items), from_cache=True)

        provider = self._factory(config)
        try:
            if provider is None:
                raise NewsProviderUnavailable(f"{config.name}: desteklenmeyen kaynak türü")
            items = provider.fetch(targets)
        except NewsProviderUnavailable as exc:
            return self._fallback(config, cached, str(exc))
        except Exception as exc:  # sağlayıcı beklenmedik hata verse bile diğer kaynaklar etkilenmez
            logger.warning("Haber kaynağı hatası (%s): %s", config.source_id, exc, exc_info=True)
            return self._fallback(config, cached, f"{type(exc).__name__}: {exc}")
        self._cache.store(key, now, items)
        return items, NewsSourceStatus(config.source_id, now, len(items))

    @staticmethod
    def _fallback(config: NewsSourceConfig, cached, error: str) -> Tuple[List[NewsItem], NewsSourceStatus]:
        """Hata durumunda varsa son başarılı çekim gösterilmeye devam eder, hata durumu raporlanır."""
        if cached:
            items = cached["items"]
            return items, NewsSourceStatus(config.source_id, cached["fetched_at"], len(items), error, True)
        return [], NewsSourceStatus(config.source_id, None, 0, error)

    @staticmethod
    def _merge(batches) -> Tuple[NewsItem, ...]:
        unique: Dict[str, NewsItem] = {}
        for batch in batches:
            for item in batch:
                existing = unique.get(item.id)
                if existing is None or item.published_at > existing.published_at:
                    unique[item.id] = item
        ordered = sorted(unique.values(), key=lambda item: item.published_at, reverse=True)
        return tuple(ordered[:MAX_ITEMS])
