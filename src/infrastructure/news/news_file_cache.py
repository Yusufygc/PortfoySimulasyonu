"""Kaynak başına son başarılı çekimi JSON dosyası olarak saklar (`data/_cache/news/`)."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.models.news_item import NewsItem
from src.domain.ports.repositories.i_news_source_repo import INewsCache

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "_cache" / "news"


def _item_to_dict(item: NewsItem) -> Dict[str, object]:
    return {
        "title": item.title, "url": item.url, "source_id": item.source_id, "source_name": item.source_name,
        "published_at": item.published_at.isoformat(), "summary": item.summary,
        "related_symbols": list(item.related_symbols), "language": item.language, "badge": item.badge,
    }


def _item_from_dict(data: Dict[str, object]) -> NewsItem:
    return NewsItem(
        title=str(data["title"]), url=str(data["url"]), source_id=str(data["source_id"]),
        source_name=str(data["source_name"]), published_at=datetime.fromisoformat(str(data["published_at"])),
        summary=str(data.get("summary", "")), related_symbols=tuple(data.get("related_symbols", ())),
        language=str(data.get("language", "tr")), badge=str(data.get("badge", "")),
    )


class JsonFileNewsCache(INewsCache):
    def __init__(self, directory: Optional[Path] = None) -> None:
        self._dir = directory or _DEFAULT_DIR

    def _path(self, key: str) -> Path:
        return self._dir / f"{hashlib.sha1(key.encode('utf-8')).hexdigest()[:20]}.json"

    def load(self, key: str) -> Optional[Dict[str, object]]:
        path = self._path(key)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return {
                "fetched_at": datetime.fromisoformat(raw["fetched_at"]),
                "items": [_item_from_dict(entry) for entry in raw["items"]],
            }
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Haber önbelleği okunamadı (%s): %s", path.name, exc)
            return None

    def store(self, key: str, fetched_at: datetime, items: List[NewsItem]) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            payload = {"fetched_at": fetched_at.isoformat(), "items": [_item_to_dict(i) for i in items]}
            self._path(key).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Haber önbelleği yazılamadı: %s", exc)
