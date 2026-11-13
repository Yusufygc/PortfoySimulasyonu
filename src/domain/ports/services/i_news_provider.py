from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from src.domain.models.news_item import NewsItem, NewsScope, NewsTarget


class NewsProviderUnavailable(Exception):
    """Kaynak ulaşılamıyor, yanıt hatalı veya ayrıştırılamıyor; diğer kaynakları etkilemez."""


class INewsProvider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def scope(self) -> NewsScope: ...

    @abstractmethod
    def fetch(self, targets: Sequence[NewsTarget]) -> list[NewsItem]:
        """Haberleri döner. COMPANY kaynaklar `targets` için, MARKET kaynaklar hedeften bağımsız çalışır.

        Hata durumunda `NewsProviderUnavailable` fırlatır; sessizce boş liste dönmez.
        """
