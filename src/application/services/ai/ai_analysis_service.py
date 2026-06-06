# -*- coding: utf-8 -*-
"""AI model analiz servisi.

Gerçek (canlı) sağlayıcı ile demo (fallback) sağlayıcı arasında bağlantı
durumuna göre seçim yapar. UI yalnızca bu servisi tüketir; concrete
istemcileri (HTTP/SDK) tanımaz.
"""

from __future__ import annotations

from src.domain.models.ai_analysis import AnalysisResult
from src.domain.ports.services.i_ai_analysis_provider import IAIAnalysisProvider


class AiAnalysisService:
    def __init__(
        self,
        live_provider: IAIAnalysisProvider,
        fallback_provider: IAIAnalysisProvider,
    ) -> None:
        self._live = live_provider
        self._fallback = fallback_provider
        self._live_available = False

    @property
    def live_available(self) -> bool:
        return self._live_available

    def probe(self) -> bool:
        """Canlı sağlayıcının erişilebilirliğini yoklar (Worker thread)."""
        self._live_available = self._live.is_available()
        return self._live_available

    def analyze(self, ticker: str) -> AnalysisResult:
        """Bağlantı varsa canlı, yoksa demo sağlayıcıyla analiz üretir (Worker thread)."""
        provider = self._live if self._live_available else self._fallback
        return provider.analyze(ticker)

    def mark_unavailable(self) -> None:
        """Analiz sırasında canlı sağlayıcı düşerse demo'ya geri dönülür."""
        self._live_available = False
