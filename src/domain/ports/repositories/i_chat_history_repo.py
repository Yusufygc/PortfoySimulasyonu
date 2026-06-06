"""Sohbet geçmişi kalıcılık port arayüzü."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models.ai_analysis import ChatSession


class IChatHistoryRepository(ABC):
    """Sohbet oturumlarını kalıcı olarak saklayan depo."""

    @abstractmethod
    def load_sessions(self) -> list[ChatSession]:
        raise NotImplementedError

    @abstractmethod
    def save_sessions(self, sessions: list[ChatSession]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_last_active_session_id(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def set_last_active_session_id(self, session_id: str | None) -> None:
        raise NotImplementedError
