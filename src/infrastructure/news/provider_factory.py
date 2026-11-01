"""Kaynak yapılandırmasından sağlayıcı üretir."""
from __future__ import annotations

from typing import Callable, Optional

from src.domain.models.news_item import NewsSourceConfig, NewsSourceKind
from src.domain.ports.services.i_news_provider import INewsProvider
from src.infrastructure.news.kap_news_provider import KapDisclosureNewsProvider
from src.infrastructure.news.rss_providers import GoogleNewsRssProvider, RssNewsProvider, YahooRssNewsProvider


class NewsProviderFactory:
    """`resolve_kap_oid`: BIST kodundan KAP üye kimliği çözen işlev (mevcut KapShareholderProvider)."""

    def __init__(self, resolve_kap_oid: Callable[[str], str]) -> None:
        self._resolve_kap_oid = resolve_kap_oid

    def __call__(self, config: NewsSourceConfig) -> Optional[INewsProvider]:
        if config.kind is NewsSourceKind.KAP:
            include_mass = str(config.options.get("include_mass_notices", "")).lower() == "true"
            return KapDisclosureNewsProvider(self._resolve_kap_oid, include_mass_notices=include_mass)
        if config.kind is NewsSourceKind.YAHOO_RSS:
            return YahooRssNewsProvider(config.source_id, config.name)
        if config.kind is NewsSourceKind.GOOGLE_NEWS:
            return GoogleNewsRssProvider(config.source_id, config.name)
        if config.kind is NewsSourceKind.RSS and config.url:
            return RssNewsProvider(config.source_id, config.name, config.url, config.language)
        return None
