"""RSS 2.0 / Atom ayrıştırıcısı (saf fonksiyonlar; ağ yok)."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional

from lxml import etree

from src.domain.models.news_item import NewsItem
from src.domain.ports.services.i_news_provider import NewsProviderUnavailable

MAX_ITEMS = 40
MAX_SUMMARY_CHARS = 280

_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def parse_feed_datetime(text: Optional[str]) -> Optional[datetime]:
    """RFC 822, ISO 8601 ve saat dilimsiz biçimleri UTC'ye çevirir; çözülemezse None."""
    if not text or not text.strip():
        return None
    value = text.strip()
    parsed: Optional[datetime] = None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clean_text(raw: Optional[str], limit: int = MAX_SUMMARY_CHARS) -> str:
    """HTML etiketlerini ve varlıklarını temizler, boşlukları sadeleştirir, uzunluğu sınırlar."""
    if not raw:
        return ""
    text = _SPACES.sub(" ", html.unescape(_TAG.sub(" ", raw))).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _child_text(element, *names: str) -> str:
    for child in element:
        if not isinstance(child.tag, str):
            continue
        if etree.QName(child).localname in names and (child.text or "").strip():
            return child.text.strip()
    return ""


def _entry_link(element) -> str:
    link = _child_text(element, "link")
    if link:
        return link
    for child in element:  # Atom: <link href="..."/>
        if isinstance(child.tag, str) and etree.QName(child).localname == "link" and child.get("href"):
            return child.get("href", "").strip()
    return _child_text(element, "guid", "id")


def parse_feed(
    content: bytes,
    *,
    source_id: str,
    source_name: str,
    language: str = "tr",
    limit: int = MAX_ITEMS,
) -> List[NewsItem]:
    """Akış gövdesini haber listesine çevirir. Başlıksız veya tarihsiz öğeler atlanır."""
    try:
        root = etree.fromstring(content, parser=etree.XMLParser(recover=True, resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as exc:
        raise NewsProviderUnavailable(f"{source_name}: akış ayrıştırılamadı ({exc})") from exc
    if root is None:
        raise NewsProviderUnavailable(f"{source_name}: akış ayrıştırılamadı")
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    if not entries:
        raise NewsProviderUnavailable(f"{source_name}: akışta haber öğesi yok")

    items: List[NewsItem] = []
    for entry in entries[:limit]:
        title = clean_text(_child_text(entry, "title"), limit=220)
        published = parse_feed_datetime(_child_text(entry, "pubDate", "published", "updated", "date"))
        url = _entry_link(entry)
        if not title or not url or published is None:
            continue
        items.append(
            NewsItem(
                title=title,
                url=url,
                source_id=source_id,
                source_name=source_name,
                published_at=published,
                summary=clean_text(_child_text(entry, "description", "summary", "encoded")),
                language=language,
            )
        )
    return items
