"""RSS tabanlı sağlayıcılar: genel piyasa akışı, Yahoo sembol akışı ve Google News aramaları."""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import Dict, List, Optional, Sequence
from urllib.parse import quote, quote_plus

from src.domain.models.news_item import NewsItem, NewsScope, NewsTarget, TargetKind
from src.domain.ports.services.i_news_provider import INewsProvider, NewsProviderUnavailable
from src.infrastructure.news._http import GetFetcher, http_get
from src.infrastructure.news.feed_parser import parse_feed

logger = logging.getLogger(__name__)

YAHOO_FEED_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"

_MAX_TARGETS = 10
_ITEMS_PER_TARGET = 8


class RssNewsProvider(INewsProvider):
    """Tek bir RSS/Atom adresinden genel piyasa haberi çeker (hedef sembollerden bağımsız)."""

    def __init__(
        self, source_id: str, display_name: str, url: str, language: str = "tr", fetcher: Optional[GetFetcher] = None
    ) -> None:
        self._source_id = source_id
        self._display_name = display_name
        self._url = url
        self._language = language
        self._fetcher = fetcher or (lambda address: http_get(address, label=display_name))

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def scope(self) -> NewsScope:
        return NewsScope.MARKET

    def fetch(self, targets: Sequence[NewsTarget]) -> List[NewsItem]:
        content = self._fetcher(self._url)
        return parse_feed(
            content, source_id=self._source_id, source_name=self._display_name, language=self._language
        )


class _PerTargetFeedProvider(INewsProvider):
    """Hedef başına bir akış çeken sağlayıcıların ortak gövdesi. Tüm hedefler başarısızsa hata verir."""

    _supported_kinds: frozenset = frozenset()
    _language = "tr"

    def __init__(self, source_id: str, display_name: str, fetcher: Optional[GetFetcher] = None) -> None:
        self._source_id = source_id
        self._display_name = display_name
        self._fetcher = fetcher or (lambda address: http_get(address, label=display_name))

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def scope(self) -> NewsScope:
        return NewsScope.COMPANY

    def _feed_url(self, target: NewsTarget) -> str:
        raise NotImplementedError

    def fetch(self, targets: Sequence[NewsTarget]) -> List[NewsItem]:
        selected = [t for t in targets if t.kind in self._supported_kinds][:_MAX_TARGETS]
        if not selected:
            return []
        items: List[NewsItem] = []
        errors: Dict[str, str] = {}
        for target in selected:
            try:
                content = self._fetcher(self._feed_url(target))
                parsed = parse_feed(
                    content, source_id=self._source_id, source_name=self._display_name, language=self._language
                )
            except NewsProviderUnavailable as exc:
                errors[target.symbol] = str(exc)
                continue
            for item in parsed[:_ITEMS_PER_TARGET]:
                items.append(_with_symbol(item, target.symbol))
        if not items and errors:
            raise NewsProviderUnavailable(f"{self._display_name}: {next(iter(errors.values()))}")
        if errors:
            logger.warning("%s: %d hedef alınamadı: %s", self._display_name, len(errors), ", ".join(errors))
        return items


def _with_symbol(item: NewsItem, symbol: str) -> NewsItem:
    return replace(item, related_symbols=(symbol,))


class YahooRssNewsProvider(_PerTargetFeedProvider):
    """ABD hissesi, kripto ve emtia için Yahoo Finance sembol akışı (İngilizce)."""

    _supported_kinds = frozenset({TargetKind.US_STOCK, TargetKind.CRYPTO, TargetKind.METAL})
    _language = "en"

    def _feed_url(self, target: NewsTarget) -> str:
        return YAHOO_FEED_URL.format(symbol=quote(target.symbol, safe="="))


class GoogleNewsRssProvider(_PerTargetFeedProvider):
    """Google News arama akışı (Türkçe). BIST için hisse koduyla, diğerleri için varlık adıyla aranır."""

    _supported_kinds = frozenset(TargetKind)
    _language = "tr"

    def _feed_url(self, target: NewsTarget) -> str:
        query = target.symbol if target.kind is TargetKind.BIST else target.name
        return GOOGLE_NEWS_URL.format(query=quote_plus(query))
