"""Haber akışı: etkin kaynakları paralel çeker, önbellekler, tekilleştirir ve tarihe göre sıralar."""
from __future__ import annotations

import hashlib
import logging
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.domain.models.news_item import (
    NewsFeedResult,
    NewsItem,
    NewsScope,
    NewsSourceConfig,
    NewsSourceKind,
    NewsSourceStatus,
    NewsTarget,
    TargetKind,
)
from src.domain.ports.repositories.i_news_source_repo import INewsCache, INewsSourceRepository
from src.domain.ports.services.i_news_provider import INewsProvider, NewsProviderUnavailable

logger = logging.getLogger(__name__)

DEFAULT_TTL = timedelta(minutes=10)
MAX_ITEMS = 150
_MAX_WORKERS = 6

ProviderFactory = Callable[[NewsSourceConfig], Optional[INewsProvider]]

# "Bağlantıyı test et" için örnek hedefler: şirket kaynakları hedefsiz çalışmaz
_PROBE_TARGETS = {
    NewsSourceKind.KAP: [NewsTarget("THYAO", "Türk Hava Yolları", TargetKind.BIST)],
    NewsSourceKind.GOOGLE_NEWS: [NewsTarget("THYAO", "Türk Hava Yolları", TargetKind.BIST)],
    NewsSourceKind.YAHOO_RSS: [NewsTarget("AAPL", "Apple", TargetKind.US_STOCK)],
}
CUSTOM_PREFIX = "rss:custom_"


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
        **options,
    ) -> None:
        """`options`: `ttl` (önbellek süresi, varsayılan 10 dk) ve `clock` (test için enjekte edilen saat)."""
        self._repo = source_repo
        self._factory = provider_factory
        self._cache = cache
        self._defaults = default_sources
        self._ttl: timedelta = options.pop("ttl", DEFAULT_TTL)
        self._clock: Callable[[], datetime] = options.pop("clock", _utc_now)
        if options:
            raise TypeError(f"Bilinmeyen seçenek: {', '.join(sorted(options))}")
        self._seeded = False
        self._last_status: Dict[str, NewsSourceStatus] = {}

    # ---------- Kaynak yönetimi ---------- #

    def list_sources(self) -> List[NewsSourceConfig]:
        self._ensure_defaults()
        return self._repo.list_sources()

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        self._repo.save_source(replace(self._get(source_id), enabled=enabled))

    def set_source_option(self, source_id: str, key: str, value: str) -> None:
        config = self._get(source_id)
        self._repo.save_source(replace(config, options={**config.options, key: value}))

    def add_rss_source(self, name: str, url: str, language: str = "tr") -> NewsSourceConfig:
        """Kullanıcının kendi RSS/Atom akışı (genel piyasa akışına eklenir). Adres http(s) olmalıdır."""
        clean_name, clean_url = (name or "").strip(), (url or "").strip()
        parsed = urlparse(clean_url)
        if not clean_name:
            raise ValueError("Besleme adı boş olamaz")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Besleme adresi http:// veya https:// ile başlamalıdır")
        source_id = CUSTOM_PREFIX + hashlib.sha1(clean_url.lower().encode("utf-8")).hexdigest()[:8]
        if any(c.source_id == source_id for c in self.list_sources()):
            raise ValueError("Bu besleme adresi zaten ekli")
        config = NewsSourceConfig(
            source_id, NewsSourceKind.RSS, clean_name, True, language if language in ("tr", "en") else "tr",
            NewsScope.MARKET, clean_url, is_custom=True,
        )
        self._repo.save_source(config)
        return config

    def remove_source(self, source_id: str) -> None:
        """Yalnızca kullanıcının eklediği RSS beslemeleri silinebilir; varsayılan kaynaklar kapatılabilir."""
        if not self._get(source_id).is_custom:
            raise ValueError("Varsayılan kaynaklar silinemez, yalnızca kapatılabilir")
        self._repo.delete_source(source_id)
        self._last_status.pop(source_id, None)

    def get_status(self, source_id: str) -> Optional[NewsSourceStatus]:
        """Bu oturumdaki son çekim veya test sonucu; hiç çekilmediyse None."""
        return self._last_status.get(source_id)

    def test_source(self, source_id: str) -> NewsSourceStatus:
        """Kaynağı önbelleksiz bir kez çeker ve sonucu döner (ağ çağrısı yapar; arka planda çağrılmalı)."""
        return self._probe(self._get(source_id))

    def test_rss_url(self, url: str, name: str = "Test") -> NewsSourceStatus:
        """Henüz eklenmemiş bir RSS adresini dener."""
        parsed = urlparse((url or "").strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return NewsSourceStatus("", error="Besleme adresi http:// veya https:// ile başlamalıdır")
        config = NewsSourceConfig("rss:test", NewsSourceKind.RSS, name or "Test", url=url.strip())
        return self._probe(config, remember=False)

    def _probe(self, config: NewsSourceConfig, remember: bool = True) -> NewsSourceStatus:
        provider = self._factory(config)
        now = self._clock()
        try:
            if provider is None:
                raise NewsProviderUnavailable(f"{config.name}: desteklenmeyen kaynak türü")
            items = provider.fetch(_PROBE_TARGETS.get(config.kind, []))
            status = NewsSourceStatus(config.source_id, now, len(items))
        except NewsProviderUnavailable as exc:
            status = NewsSourceStatus(config.source_id, None, 0, str(exc))
        except Exception as exc:
            status = NewsSourceStatus(config.source_id, None, 0, f"{type(exc).__name__}: {exc}")
        if remember:
            self._last_status[config.source_id] = status
        return status

    def _get(self, source_id: str) -> NewsSourceConfig:
        for config in self.list_sources():
            if config.source_id == source_id:
                return config
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
            return items, self._remember(NewsSourceStatus(config.source_id, cached["fetched_at"], len(items), from_cache=True))

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
        return items, self._remember(NewsSourceStatus(config.source_id, now, len(items)))

    def _remember(self, status: NewsSourceStatus) -> NewsSourceStatus:
        self._last_status[status.source_id] = status
        return status

    def _fallback(self, config: NewsSourceConfig, cached, error: str) -> Tuple[List[NewsItem], NewsSourceStatus]:
        """Hata durumunda varsa son başarılı çekim gösterilmeye devam eder, hata durumu raporlanır."""
        if cached:
            items = cached["items"]
            return items, self._remember(
                NewsSourceStatus(config.source_id, cached["fetched_at"], len(items), error, True)
            )
        return [], self._remember(NewsSourceStatus(config.source_id, None, 0, error))

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
