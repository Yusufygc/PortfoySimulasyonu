from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.models.news_item import NewsItem, NewsSourceConfig


class INewsSourceRepository(ABC):
    @abstractmethod
    def list_sources(self) -> List[NewsSourceConfig]: ...

    @abstractmethod
    def save_source(self, config: NewsSourceConfig) -> None:
        """Ekler veya `source_id` üzerinden günceller."""

    @abstractmethod
    def delete_source(self, source_id: str) -> None: ...


class INewsCache(ABC):
    """Kaynak başına son başarılı çekimin önbelleği (yeniden başlatmada ve çevrimdışıyken gösterim için)."""

    @abstractmethod
    def load(self, key: str) -> Optional[Dict[str, object]]:
        """`{"fetched_at": datetime, "items": list[NewsItem]}` veya yoksa None."""

    @abstractmethod
    def store(self, key: str, fetched_at, items: List[NewsItem]) -> None: ...
