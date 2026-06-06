"""AI model analiz sağlayıcısı port arayüzü."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.ai_analysis import AnalysisResult


class IAIAnalysisProvider(ABC):
    """Bir hisse için model analizi üreten kaynak (gerçek API veya demo)."""

    @abstractmethod
    def analyze(self, ticker: str) -> AnalysisResult:
        """Senkron çağrı. UI Worker içinde çalıştırılır."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Sağlayıcı erişilebilir mi? UI banner/fallback için."""
        raise NotImplementedError
