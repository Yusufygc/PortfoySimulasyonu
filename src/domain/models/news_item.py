"""Haber akışı modelleri: haber öğesi, takip hedefi, kaynak yapılandırması ve kaynak durumu."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping, Optional, Tuple


class NewsScope(str, Enum):
    """Kaynağın hangi akışa haber verdiği."""

    COMPANY = "company"  # takip edilen sembollere bağlı haber
    MARKET = "market"  # sembolsüz genel piyasa / global akış


class NewsSourceKind(str, Enum):
    KAP = "kap"
    YAHOO_RSS = "yahoo_rss"
    GOOGLE_NEWS = "google_news"
    RSS = "rss"


class TargetKind(str, Enum):
    """Haber sorgusu yapılacak varlığın türü; sağlayıcı kendi desteklediği türleri seçer."""

    BIST = "bist"
    US_STOCK = "us_stock"
    CRYPTO = "crypto"
    METAL = "metal"


@dataclass(frozen=True)
class NewsTarget:
    """Haber aranacak bir varlık. `symbol` BIST kodu veya yfinance sembolü, `name` görünen ad."""

    symbol: str
    name: str
    kind: TargetKind


@dataclass(frozen=True)
class NewsItem:
    """Tek haber; yalnızca başlık, kısa özet ve bağlantı saklanır (tam metin yok)."""

    title: str
    url: str
    source_id: str
    source_name: str
    published_at: datetime  # saat dilimli (UTC)
    summary: str = ""
    related_symbols: Tuple[str, ...] = ()
    language: str = "tr"
    badge: str = ""  # kaynağa özgü kısa etiket (ör. KAP bildirim sınıfı)

    @property
    def id(self) -> str:
        """Tekilleştirme anahtarı: bağlantı, yoksa normalize başlık."""
        basis = self.url.strip().lower() if self.url.strip() else normalize_title(self.title)
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class NewsSourceConfig:
    """Ayarlar'dan yönetilen haber kaynağı. `url` yalnızca RSS türünde anlamlıdır."""

    source_id: str
    kind: NewsSourceKind
    name: str
    enabled: bool = True
    language: str = "tr"
    scope: NewsScope = NewsScope.MARKET
    url: str = ""
    description: str = ""
    is_custom: bool = False
    options: Mapping[str, str] = field(default_factory=dict)  # kaynağa özgü seçenekler (ör. include_mass_notices)


@dataclass(frozen=True)
class NewsSourceStatus:
    """Bir kaynağın son çekim sonucu; `error` doluysa kaynak ulaşılamıyor demektir."""

    source_id: str
    fetched_at: Optional[datetime] = None
    item_count: int = 0
    error: str = ""
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return not self.error


@dataclass(frozen=True)
class NewsFeedResult:
    items: Tuple[NewsItem, ...] = ()
    statuses: Tuple[NewsSourceStatus, ...] = field(default_factory=tuple)

    @property
    def failed_sources(self) -> Tuple[str, ...]:
        return tuple(s.source_id for s in self.statuses if not s.ok)


_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_title(title: str) -> str:
    """Tekilleştirme için başlığı küçük harfe indirip noktalama ve fazla boşlukları atar."""
    lowered = title.casefold()
    return _WHITESPACE.sub(" ", _PUNCT.sub(" ", lowered)).strip()
