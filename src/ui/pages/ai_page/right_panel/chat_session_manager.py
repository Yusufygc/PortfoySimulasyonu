"""Sohbet oturumu yönetimi (UI tarafı).

Kalıcılığı enjekte edilen `IChatHistoryRepository` portuna devreder; kullanıcıya
dönük varsayılan içerikleri (karşılama mesajı, başlık) L10N üzerinden üretir.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole
from src.domain.ports.repositories.i_chat_history_repo import IChatHistoryRepository
from src.ui.pages.ai_page.labels import EMPTY_CHAT_TITLE, WELCOME_MESSAGE

MAX_TITLE_LENGTH = 48


class ChatSessionManager:
    """Repo üzerinde sohbet oturumlarını yönetir ve içerik varsayılanları üretir."""

    def __init__(self, repo: IChatHistoryRepository) -> None:
        self._repo = repo

    @property
    def repo(self) -> IChatHistoryRepository:
        return self._repo

    # ── Kalıcılık (port'a devir) ─────────────────────────────────────────

    def load_sessions(self) -> list[ChatSession]:
        return self._repo.load_sessions()

    def save_sessions(self, sessions: list[ChatSession]) -> None:
        self._repo.save_sessions(sessions)

    def get_last_active_session_id(self) -> str | None:
        return self._repo.get_last_active_session_id()

    def set_last_active_session_id(self, session_id: str | None) -> None:
        self._repo.set_last_active_session_id(session_id)

    # ── İçerik yardımcıları ──────────────────────────────────────────────

    def create_session(
        self,
        messages: list[ChatMessage] | None = None,
        title: str = EMPTY_CHAT_TITLE,
    ) -> ChatSession:
        now = datetime.now()
        return ChatSession(
            id=uuid4().hex,
            title=title,
            messages=list(messages or []),
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def default_messages() -> list[ChatMessage]:
        return [ChatMessage(MessageRole.AI, WELCOME_MESSAGE)]

    @staticmethod
    def title_from_message(text: str) -> str:
        compact = " ".join(text.strip().split())
        if not compact:
            return EMPTY_CHAT_TITLE
        if len(compact) <= MAX_TITLE_LENGTH:
            return compact
        return compact[: MAX_TITLE_LENGTH - 1].rstrip() + "…"
