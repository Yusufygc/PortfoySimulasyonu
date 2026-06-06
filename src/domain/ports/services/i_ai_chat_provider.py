"""AI sohbet (LLM) sağlayıcısı port arayüzü."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence, Tuple


class IAIChatProvider(ABC):
    """Sistem talimatı + sıralı sohbet turlarından yanıt üreten LLM sağlayıcı."""

    @abstractmethod
    def generate(self, system_prompt: str, turns: Sequence[Tuple[str, str]]) -> str:
        """Yanıt üretir.

        Args:
            system_prompt: Sistem talimatı (system instruction).
            turns: ``(role, text)`` çiftleri; ``role`` "user" veya "model".
                Son tur sıradaki kullanıcı/sistem mesajıdır.
        """
        raise NotImplementedError
